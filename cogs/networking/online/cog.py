# cogs/online/cog.py
from __future__ import annotations

import logging
import discord
from discord.ext import commands

from configs.config_general import BOT_GUILD_ID
from configs.config_channels import LOGS_CHANNEL_ID
from configs.helper import send_as_webhook

from .filters import has_allowed_role, OFFLINE_STATES, ONLINE_DEST_STATES

class PresenceLogger(commands.Cog):
    """Logs OFFLINE→ONLINE presence changes to a logs channel for specific roles."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)

    @commands.Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        # Only within the configured guild
        if after.guild is None or after.guild.id != int(BOT_GUILD_ID):
            return

        # Ignore bots
        if after.bot:
            return

        # Only members with allowed roles
        if not has_allowed_role(after):
            return

        before_status = getattr(before, "status", None)
        after_status = getattr(after, "status", None)

        # No-op/unknown
        if before_status is None or after_status is None or before_status == after_status:
            return

        # Only OFFLINE/INVISIBLE -> ONLINE/IDLE/DND
        if before_status not in OFFLINE_STATES or after_status not in ONLINE_DEST_STATES:
            return

        # Resolve logs channel
        logs_channel = (
            after.guild.get_channel(int(LOGS_CHANNEL_ID))
            or self.bot.get_channel(int(LOGS_CHANNEL_ID))
        )
        if logs_channel is None:
            try:
                logs_channel = await self.bot.fetch_channel(int(LOGS_CHANNEL_ID))
            except Exception:
                self.log.warning(f"[PresenceLogger] Could not resolve LOGS_CHANNEL_ID={LOGS_CHANNEL_ID}")
                return

        # Minimal embed: avatar + “is Online!”; always green
        embed = discord.Embed(color=discord.Color.green())
        embed.set_author(
            name=f"{after.display_name} is Online!",
            icon_url=after.display_avatar.url,
        )

        try:
            await send_as_webhook(logs_channel, "online", embed=embed)
        except Exception:
            self.log.error("[PresenceLogger] Failed to send presence embed", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PresenceLogger(bot))
