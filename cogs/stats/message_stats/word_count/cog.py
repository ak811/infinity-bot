# cogs/message_stats/word_count/cog.py
from __future__ import annotations

import discord
from discord.ext import commands

from .storage import safe_load_word_counts, persist_word_counts
from .tokenizer import extract_valid_words

class WordCountCog(commands.Cog):
    """Counts real words per user and persists them to WORDS_FILE."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        # Ignore bots & DMs (your original call site already filtered bots; we mirror that)
        if message.author.bot or message.guild is None:
            return

        words = extract_valid_words(message.content or "")
        if not words:
            return

        data = safe_load_word_counts()
        user_key = str(message.author.id)
        bucket = data.get(user_key)
        if not isinstance(bucket, dict):
            bucket = {}
            data[user_key] = bucket

        for w in words:
            bucket[w] = int(bucket.get(w, 0)) + 1

        persist_word_counts(data)

async def setup(bot: commands.Bot):
    await bot.add_cog(WordCountCog(bot))
