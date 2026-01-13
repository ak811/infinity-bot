# cogs/message_stats/message_count/cog.py
from __future__ import annotations

import discord
from discord.ext import commands
from .storage import increment_user_message_count

class MessageCountCog(commands.Cog):
    """Increments a per-user message counter on every guild message."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        # Ignore bots & DMs to match common gating
        if message.author.bot or message.guild is None:
            return
        increment_user_message_count(message.author.id)

async def setup(bot: commands.Bot):
    await bot.add_cog(MessageCountCog(bot))
