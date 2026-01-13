# cogs/word_snake/cog.py
from __future__ import annotations

import re
import logging

import discord
from discord.ext import commands

from configs.config_channels import WORD_SNAKE_CHANNEL_ID
from .dictionary import WordDictionary

WORD_SNAKE_PATTERN = re.compile(r"^[A-Za-z]+$")

class WordSnakeCog(commands.Cog):
    """Moderates the Word Snake channel with dictionary & turn-taking rules."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.dict = WordDictionary()

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        # Only watch the configured channel
        if not isinstance(message.channel, discord.TextChannel) or message.channel.id != WORD_SNAKE_CHANNEL_ID:
            return

        # Ignore bots (lets mods/bots post explanations)
        if message.author.bot:
            return

        content_raw = message.content.strip()
        logging.debug(f"[WordSnake] Received: '{content_raw}' from {message.author} ({message.author.id})")

        # Basic format
        if len(content_raw) < 2 or not WORD_SNAKE_PATTERN.fullmatch(content_raw):
            logging.info(f"[WordSnake] Delete invalid format: '{content_raw}'")
            await self._safe_delete(message)
            return

        word = content_raw.lower()

        # Dictionary membership
        words = self.dict.words()
        if word not in words:
            logging.info(f"[WordSnake] Delete non-dictionary word: '{content_raw}'")
            await self._safe_delete(message)
            return

        # Need at least one prior message to compare turn + last char
        history = [msg async for msg in message.channel.history(limit=2)]
        if len(history) < 2:
            logging.info("[WordSnake] Delete: insufficient history.")
            await self._safe_delete(message)
            return

        previous = history[1]
        prev_text = (previous.content or "").strip().lower()
        last_char = prev_text[-1] if prev_text else None

        # Same word twice
        if word == prev_text:
            logging.info(f"[WordSnake] Delete: same word repeated '{content_raw}'")
            await self._safe_delete(message)
            return

        # Must start with last char of previous
        if last_char and not word.startswith(last_char):
            logging.info(f"[WordSnake] Delete '{content_raw}' — does not start with '{last_char}'")
            await self._safe_delete(message)
            return

        # No back-to-back turns by same author
        if message.author.id == previous.author.id:
            logging.info(f"[WordSnake] Delete: same user twice {message.author}")
            await self._safe_delete(message)
            return

        # Valid move ✅
        try:
            await message.add_reaction("✅")
            logging.debug(f"[WordSnake] Accepted: '{content_raw}'")
        except Exception as e:
            logging.debug(f"[WordSnake] Failed to react OK: {e}")

    async def _safe_delete(self, message: discord.Message):
        try:
            await message.delete()
        except Exception as e:
            logging.debug(f"[WordSnake] Failed to delete message {getattr(message, 'id', 'unknown')}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(WordSnakeCog(bot))
