# cogs/transcription/detectors.py
from __future__ import annotations
import discord

def is_voice_message(message: discord.Message) -> bool:
    """
    Try to detect voice messages across discord.py versions.

    - Prefer message.flags.voice if available.
    - Fallback to checking attachments for audio content types or common voice indicators.
    """
    try:
        if getattr(message.flags, "voice", False):
            return True
    except Exception:
        pass

    for att in message.attachments:
        ct = (att.content_type or "").lower()
        name = (att.filename or "").lower()
        if ct.startswith("audio/"):
            return True
        if name.endswith((".ogg", ".m4a", ".mp3", ".wav", ".webm")) or "voice" in name:
            return True

    return False
