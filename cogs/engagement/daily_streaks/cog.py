# cogs/daily_streaks/cog.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from .service import process_daily_streak, process_daily_streak_for
from configs.config_general import BOT_GUILD_ID

class DailyStreaksCog(commands.Cog):
    """
    Triggers the daily streak award on any activity:
      • Message in guild
      • Reaction add in guild
      • Voice-channel join/switch in guild
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)

    # ---------------------------
    # Message activity
    # ---------------------------
    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return
        if message.guild.id != int(BOT_GUILD_ID):
            return
        try:
            await process_daily_streak(message)
        except Exception:
            self.log.exception("[DailyStreaks] on_message failed")

    # ---------------------------
    # Reaction activity
    # ---------------------------
    @commands.Cog.listener("on_reaction_add")
    async def on_reaction_add_listener(self, reaction: discord.Reaction, user: discord.User | discord.Member):
        # Reaction may be on DMs or from bots — skip those
        msg = reaction.message
        guild = getattr(msg, "guild", None)
        if guild is None or getattr(user, "bot", False):
            return
        if guild.id != int(BOT_GUILD_ID):
            return
        try:
            await process_daily_streak_for(
                guild=guild,
                user=user,
                created_at=datetime.now(timezone.utc),
            )
        except Exception:
            self.log.exception("[DailyStreaks] on_reaction_add failed")

    # ---------------------------
    # Voice activity
    # ---------------------------
    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update_listener(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        # Ignore bots/other guilds
        if member.bot or member.guild is None:
            return
        if member.guild.id != int(BOT_GUILD_ID):
            return

        # Trigger on net join or channel switch INTO a channel
        joined = after.channel and (before.channel != after.channel)
        if not joined:
            return

        try:
            await process_daily_streak_for(
                guild=member.guild,
                user=member,
                created_at=datetime.now(timezone.utc),
            )
        except Exception:
            self.log.exception("[DailyStreaks] on_voice_state_update failed")


async def setup(bot: commands.Bot):
    await bot.add_cog(DailyStreaksCog(bot))
