# cogs/transcription/cog.py
from __future__ import annotations

import io
import discord
from discord.ext import commands

from configs.config_logging import logging
from configs.config_general import BOT_GUILD_ID
# Optional: restrict to one channel
# from configs.config_channels import VOICE_CHAT_CHANNEL_ID

from .detectors import is_voice_message
from .service import SpeechToText, NullSTT
from .tasks import schedule as schedule_tasks


class TranscriptionCog(commands.Cog):
    """Transcribe voice messages and post text back to the channel (or elsewhere)."""

    def __init__(self, bot: commands.Bot, stt: SpeechToText | None = None):
        self.bot = bot
        self.stt: SpeechToText = stt or NullSTT()

    # Public method so you can call it from tests/elsewhere if you want
    async def process_transcription(self, message: discord.Message) -> None:
        # Wrong place or bot author
        if not message.guild or message.guild.id != BOT_GUILD_ID or message.author.bot:
            return

        # Optional: scope to a single channel
        # if message.channel.id != VOICE_CHAT_CHANNEL_ID:
        #     return

        if not is_voice_message(message):
            return

        audio_attachments = [
            att for att in message.attachments
            if (att.content_type or "").lower().startswith("audio/")
            or att.filename.lower().endswith((".ogg", ".m4a", ".mp3", ".wav", ".webm"))
            or "voice" in att.filename.lower()
        ]
        if not audio_attachments:
            return

        coros = [self._download_transcribe_and_reply(message, att) for att in audio_attachments]
        if schedule_tasks:
            schedule_tasks(coros)
        else:
            # No scheduler available — run sequentially
            for c in coros:
                await c

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message):
        await self.process_transcription(message)

    async def _download_transcribe_and_reply(self, message: discord.Message, attachment: discord.Attachment) -> None:
        try:
            raw = await attachment.read()
            audio_bytes = io.BytesIO(raw)
            filename = attachment.filename or "audio"

            logging.info(f"[Transcription] Downloaded {len(raw)} bytes from {filename} (msg {message.id})")

            text = await self.stt.transcribe(audio_bytes=audio_bytes, filename=filename, user_id=message.author.id)
            if not text:
                logging.info(f"[Transcription] Empty transcript for {filename}")
                return

            reply = f"🗣️ **Transcription** ({filename}):\n{text[:1900]}"
            await message.reply(reply, mention_author=False)

            logging.info(f"[Transcription] Posted transcript for {filename} (msg {message.id})")

        except Exception as e:
            logging.warning(f"[Transcription] Failed processing {getattr(attachment, 'filename', 'unknown')}: {e}")


async def setup(bot: commands.Bot):
    # If you have a real STT, inject here instead of NullSTT()
    await bot.add_cog(TranscriptionCog(bot, stt=NullSTT()))
