# cogs/stats/logging/delete/cog.py
from __future__ import annotations

import discord
from discord.ext import commands
from .core import log_message_delete


class DeleteLoggingCog(commands.Cog):
    """Logs message deletions."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        await log_message_delete(self.bot, message)
