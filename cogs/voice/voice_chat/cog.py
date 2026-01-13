# cogs/voice_chat/cog.py
from __future__ import annotations

import discord
from discord.ext import commands

from configs.config_general import BOT_GUILD_ID
from configs.config_channels import VOICE_CHAT_CHANNEL_ID
from configs.config_logging import logging

from .detectors import is_voice_message


class VoiceChatGatekeeper(commands.Cog):
    """
    Deletes any *new* non-voice messages posted in VOICE_CHAT_CHANNEL_ID,
    except messages from bots.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        # Wrong guild or DMs
        if not message.guild or message.guild.id != BOT_GUILD_ID:
            return

        # Only target the configured voice-chat text channel
        if message.channel.id != VOICE_CHAT_CHANNEL_ID:
            return

        # Allow all bot messages (announcements, system, etc.)
        if message.author.bot:
            return

        # Keep voice messages
        if is_voice_message(message):
            return

        # Delete everything else (no 'reason' for cross-version compatibility)
        try:
            await message.delete()
            logging.info(
                f"[VoiceChat] Deleted non-voice message {message.id} from {message.author} in #{message.channel.name}"
            )
        except Exception as e:
            logging.warning(
                f"[VoiceChat] Failed to delete message {getattr(message, 'id', 'unknown')}: {e}"
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceChatGatekeeper(bot))
