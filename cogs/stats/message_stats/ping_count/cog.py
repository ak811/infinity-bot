# cogs/message_stats/pings_count/cog.py
from __future__ import annotations

import discord
from discord.ext import commands

from .storage import load_counts, save_counts, load_detail, save_detail


class PingsCountCog(commands.Cog):
    """
    Logs @mentions:
      - PING_COUNTS_FILE: total pings received per user
      - PING_DETAIL_FILE: per-sender ping breakdown
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        # Keep behavior aligned with typical on_message gating
        if message.author.bot:
            return
        if not message.guild:  # ignore DMs
            return
        if not message.mentions:
            return

        counts = load_counts()
        detail = load_detail()

        author_key = str(message.author.id)
        author_bucket = detail.setdefault(author_key, {})

        for m in message.mentions:
            target_key = str(m.id)
            counts[target_key] = counts.get(target_key, 0) + 1
            author_bucket[target_key] = author_bucket.get(target_key, 0) + 1

        save_counts(counts)
        save_detail(detail)


async def setup(bot: commands.Bot):
    await bot.add_cog(PingsCountCog(bot))
