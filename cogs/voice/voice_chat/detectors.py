# cogs/voice_chat/detectors.py
from __future__ import annotations
import discord

def is_voice_message(message: discord.Message) -> bool:
    """
    Try to detect voice messages across discord.py versions.

    - Prefer message.flags.voice if available.
    - Fallback to checking attachments for audio content types or common voice indicators.
    """
    # Newer versions: message.flags.voice
    try:
        if getattr(message.flags, "voice", False):
            return True
    except Exception:
        pass

    # Fallback: check attachments/content-types/filenames
    for att in message.attachments:
        ct = (att.content_type or "").lower()
        name = (att.filename or "").lower()

        # Voice messages are typically small .ogg (opus) or audio/*
        if ct.startswith("audio/"):
            return True
        if name.endswith(".ogg") or "voice" in name or name.endswith((".m4a", ".mp3", ".wav", ".webm")):
            return True

    return False
