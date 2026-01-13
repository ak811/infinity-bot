from __future__ import annotations
import re, unicodedata
from typing import Iterable, List
import discord
from configs.helper import send_as_webhook
from .constants import FIELD_VALUE_LIMIT, FIELD_NAME_LIMIT, FIELDS_PER_EMBED_LIMIT

def normalize(s: str | None) -> str:
    if not s:
        return ""
    s = s.replace("–", "-").replace("—", "-").replace("\\", "/")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9/\+\-\s]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()

def chunk_lines(lines: Iterable[str], limit: int = FIELD_VALUE_LIMIT):
    chunk, length = [], 0
    for line in lines:
        extra = len(line) + (1 if chunk else 0)
        if length + extra > limit:
            if chunk: yield "\n".join(chunk)
            if len(line) > limit: yield line[:limit - 1] + "…"; chunk, length = [], 0
            else: chunk, length = [line], len(line)
        else:
            chunk.append(line); length += extra
    if chunk: yield "\n".join(chunk)

def add_field_safely(embed: discord.Embed, name: str, value: str):
    name = name if len(name) <= FIELD_NAME_LIMIT else name[:FIELD_NAME_LIMIT - 1] + "…"
    embed.add_field(name=name, value=value, inline=False)

def ensure_capacity(embeds: List[discord.Embed], current: discord.Embed) -> discord.Embed:
    if len(current.fields) >= FIELDS_PER_EMBED_LIMIT:
        embeds.append(current)
        current = discord.Embed(title="📋 Server Role Stats (cont.)", color=discord.Color.blue())
    return current

async def send_embed(ctx, embed: discord.Embed, *, view: discord.ui.View | None = None):
    try:
        return await send_as_webhook(ctx, "roles", embed=embed, view=view)
    except TypeError:
        return await send_as_webhook(ctx, "roles", embed=embed)
