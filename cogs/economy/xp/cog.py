# cogs/xp/cog.py
from __future__ import annotations

import logging
import discord
from discord.ext import commands

from .antispam import handle_xp_with_antispam
from .commands import XPCommands

class XPEvents(commands.Cog):
    """Listens to messages and applies spam-guarded XP updates."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        # Ignore bots & DMs
        if message.author.bot or message.guild is None:
            return
        try:
            handle_xp_with_antispam(message.author.id, message.content or "")
        except Exception:
            self.log.exception("[XP] on_message handling failed")

async def setup(bot: commands.Bot):
    # Add both the events listener and the command cog
    await bot.add_cog(XPEvents(bot))
    await bot.add_cog(XPCommands(bot))
