# cogs/ping/main.py
from __future__ import annotations
import discord
from discord.ext import commands

from .config import ALLOW_OPTIONAL_MESSAGE
from .permissions import (
    can_use_here,
    is_elite_plus,
    is_pingable_elite_plus,
    role_ladder_index,
)
from .resolve import resolve_role
from .ratelimit import (
    check_user_cooldown, stamp_user_cooldown,
    check_role_cooldown, stamp_role_cooldown,
)
from .messages import embed_err, embed_info, embed_ok
from .notify import send_ping
from configs.helper import send_as_webhook

class PingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ping")
    async def ping_cmd(self, ctx: commands.Context, *, args: str = None):
        """
        Usage:
          !ping <role> [message...]
        - Only Elite+ can run this command.
        - Only Elite+ ladder roles can be pinged.
        - Optional message is allowed (can be disabled in config).
        """
        # Channel gate
        if not await can_use_here(ctx):
            return

        # Permissions (caller)
        if not is_elite_plus(ctx.author):
            e = embed_err("⛔ Permission denied", "Only **Captain+** members can use `!ping`.")
            await send_as_webhook(ctx, "ping", embed=e)
            return

        if not args:
            e = embed_info("🔔 Usage", "Use `!ping <role> [message...]`")
            await send_as_webhook(ctx, "ping", embed=e)
            return

        # Split first token as role query; rest as message
        parts = args.strip().split()
        role_query = parts[0]
        message = " ".join(parts[1:]) if len(parts) > 1 else None
        if not ALLOW_OPTIONAL_MESSAGE:
            message = None

        # Resolve role
        role = await resolve_role(ctx.guild, role_query)
        if not role:
            e = embed_err("🔎 Role not found", f"I couldn't resolve a role from **{role_query}**.")
            await send_as_webhook(ctx, "ping", embed=e)
            return

        # Target must be Elite+ role (in the ladder & >= threshold)
        if not is_pingable_elite_plus(role):
            ladder_idx = role_ladder_index(role)
            if ladder_idx < 0:
                extra = "This role is not part of the Elite ladder."
            else:
                extra = "This role is below **Elite** in the ladder."
            e = embed_err("🚫 Not allowed to ping that role", extra)
            await send_as_webhook(ctx, "ping", embed=e)
            return

        # Cooldowns
        rem_user = check_user_cooldown(ctx.guild.id, ctx.author.id)
        if rem_user > 0:
            e = embed_info("⏳ Slow down", f"You can use `!ping` again in **{rem_user}s**.")
            await send_as_webhook(ctx, "ping", embed=e)
            return

        rem_role = check_role_cooldown(ctx.guild.id, role.id)
        if rem_role > 0:
            e = embed_info("🕐 Recently pinged", f"{role.mention} was pinged recently. Try again in **{rem_role}s**.")
            await send_as_webhook(ctx, "ping", embed=e)
            return

        # Send the ping
        await send_ping(ctx, role, message)

        # Stamp cooldowns
        stamp_user_cooldown(ctx.guild.id, ctx.author.id)
        stamp_role_cooldown(ctx.guild.id, role.id)

# === Setup ===
async def setup(bot):
    await bot.add_cog(PingCog(bot))
