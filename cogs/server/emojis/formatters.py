# cogs/server/emojis/formatters.py
from __future__ import annotations
import discord
from datetime import datetime, timezone

def emoji_url(e: discord.Emoji) -> str:
    ext = "gif" if e.animated else "png"
    return f"https://cdn.discordapp.com/emojis/{e.id}.{ext}?v=1"

def sticker_url(s: discord.GuildSticker) -> str:
    return getattr(s, "url", None) or str(getattr(s, "asset", ""))

def created_at_from_snowflake(id_: int) -> datetime:
    # Discord epoch-based snowflake
    ts_ms = ((id_ >> 22) + 1420070400000)
    return datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)

def emoji_row(e: discord.Emoji) -> str:
    token = f"<{'a' if e.animated else ''}:{e.name}:{e.id}>"
    locked = " 🔒" if e.roles else ""
    return f"{token}{locked}"

def sticker_row(s: discord.GuildSticker) -> str:
    fmt = getattr(s, "format", getattr(s, "format_type", None))
    label = "LOTTIE" if str(fmt).endswith("lottie") else "PNG/APNG"
    return f":{s.name}: ({label})"
