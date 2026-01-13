# cogs/server/emojis/categorize.py
from __future__ import annotations
import discord
from typing import Dict, List
from .constants import (
    CAT_EMOJI_ANIM, CAT_EMOJI_STATIC, CAT_STICKER_LOTTIE, CAT_STICKER_STATIC
)
from .formatters import emoji_row, sticker_row

def emojis(emojis: List[discord.Emoji]) -> Dict[str, List[str]]:
    buckets = {CAT_EMOJI_ANIM: [], CAT_EMOJI_STATIC: []}
    for e in emojis:
        (buckets[CAT_EMOJI_ANIM] if e.animated else buckets[CAT_EMOJI_STATIC]).append(emoji_row(e))
    for k in buckets:
        buckets[k].sort(key=str.casefold)
    return {k: v for k, v in buckets.items() if v}

def stickers(stickers: List[discord.GuildSticker]) -> Dict[str, List[str]]:
    b = {CAT_STICKER_LOTTIE: [], CAT_STICKER_STATIC: []}
    for s in stickers:
        fmt = getattr(s, "format", getattr(s, "format_type", None))
        (b[CAT_STICKER_LOTTIE] if str(fmt).endswith("lottie") else b[CAT_STICKER_STATIC]).append(sticker_row(s))
    for k in b:
        b[k].sort(key=str.casefold)
    return {k: v for k, v in b.items() if v}
