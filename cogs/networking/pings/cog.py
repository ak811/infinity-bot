# cogs/networking/pings/cog.py
from __future__ import annotations

import logging
from typing import Optional, Dict

import discord
from discord.ext import commands

from configs.helper import send_as_webhook
from configs.config_channels import BOTS_PLAYGROUND_CHANNEL_ID

from .storage import (
    get_user_ping_state,
    set_user_ping_state,
    get_ping_mode_text,
    PING_STATE_OFF,
    PING_STATE_ON,
    PING_STATE_ONLINE_ONLY,
    load_ping_counts,
    load_ping_detail,
    # load_ping_toggles,  # ← uncomment if/when you use filters for selection
)
from .formatting import build_stats_lines, build_server_top_lines
# from .filters import select_eligible_users, shuffled_mentions  # ← available for future commands

class Pings(commands.Cog):
    """
    `!pings` command family:
      - !pings                      : show list of commands
      - !pings stats [/ @user]      : personal stats
      - !pings top                  : server-wide most-pinged users
      - !pings on|off|online        : set receive mode
      - !pings mode                 : show your current mode
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)

    # Root group — shows commands list
    @commands.group(name="pings", invoke_without_command=True)
    async def pings(self, ctx: commands.Context, *, _rest: Optional[str] = None):
        await self._send_commands_embed(ctx)

    @pings.command(name="stats")
    async def pings_stats(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        target = member or (ctx.message.mentions[0] if ctx.message.mentions else ctx.author)
        await self._send_stats_embed(ctx, target)

    @pings.command(name="top")
    async def pings_top(self, ctx: commands.Context):
        data: Dict[str, int] = load_ping_counts()
        if not data:
            return await send_as_webhook(ctx.channel, "pings", content="⚠️ No ping data available yet.")
        lines = build_server_top_lines(data, ctx.guild, limit=10)
        embed = discord.Embed(
            title="📊 Top 10 Most-Pinged Users",
            description="\n".join(lines),
            color=discord.Color.green(),
        )
        embed.set_footer(text="Based on recent ping tracking")
        await send_as_webhook(ctx.channel, "pings", embed=embed)

    @pings.command(name="mode")
    async def pings_mode_show(self, ctx: commands.Context):
        state = get_user_ping_state(ctx.author.id)
        content = f"🔔 Your current ping mode is **{get_ping_mode_text(state)}**."
        await send_as_webhook(ctx.channel, "pings", content=content)

    @pings.command(name="on")
    async def pings_on(self, ctx: commands.Context):
        set_user_ping_state(ctx.author.id, PING_STATE_ON)
        content = "🔔 Ping mode updated: **on ✅**. You'll receive pings regardless of status."
        await send_as_webhook(ctx.channel, "pings", content=content)

    @pings.command(name="off")
    async def pings_off(self, ctx: commands.Context):
        set_user_ping_state(ctx.author.id, PING_STATE_OFF)
        content = "🔔 Ping mode updated: **off 🙅**. You won't receive pings."
        await send_as_webhook(ctx.channel, "pings", content=content)

    @pings.command(name="online")
    async def pings_online(self, ctx: commands.Context):
        set_user_ping_state(ctx.author.id, PING_STATE_ONLINE_ONLY)
        content = "🔔 Ping mode updated: **online-only 🟢**. I'll only ping you when your status is **Online** or **Idle**."
        await send_as_webhook(ctx.channel, "pings", content=content)

    # Backward-compatible alias
    @commands.command(name="top_pings")
    async def top_pings_alias(self, ctx: commands.Context):
        if not await _ensure_allowed(ctx):
            return
        await self.pings_top(ctx)

    # Internals ----------------------------------------------------
    async def _send_stats_embed(self, ctx: commands.Context, member: discord.Member):
        data = load_ping_detail()
        entry = data.get(str(member.id), {})
        if not entry:
            content = f"⚠️ No ping details found for **{member.display_name}**."
            return await send_as_webhook(ctx.channel, "pings", content=content)

        lines = build_stats_lines(entry, ctx.guild, limit=10)
        state = get_user_ping_state(member.id)

        embed = discord.Embed(
            title=f"📨 Top 10 Users Pinged by {member.display_name}",
            description="\n".join(lines),
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Your current mode: {get_ping_mode_text(state)}")
        await send_as_webhook(ctx.channel, "pings", embed=embed)

    async def _send_commands_embed(self, ctx: commands.Context):
        state = get_user_ping_state(ctx.author.id)
        embed = discord.Embed(
            title="Ping commands",
            description=(
                "**Stats**\n"
                "• `!pings` — show the list of ping commands\n"
                "• `!pings stats` — show your top pings\n"
                "• `!pings stats @user` — show a user's top pings\n\n"
                "**Server Top**\n"
                "• `!pings top` — show server-wide most-pinged users\n\n"
                "**Mode**\n"
                "• `!pings on` — always receive pings\n"
                "• `!pings off` — never receive pings\n"
                "• `!pings online` — receive pings only when you're Online (🟢) or Idle (🟡)\n"
                "• `!pings mode` — show your current mode\n"
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Your current mode: {get_ping_mode_text(state)}")
        await send_as_webhook(ctx.channel, "pings", embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Pings(bot))
