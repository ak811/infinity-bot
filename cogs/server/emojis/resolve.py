# cogs/server/emojis/resolve.py
from __future__ import annotations
import discord
from typing import List, Optional

def _match_by_name(items, name: str):
    n = name.casefold()
    exact = [x for x in items if getattr(x, "name", "").casefold() == n]
    if exact: return exact
    prefix = [x for x in items if getattr(x, "name", "").casefold().startswith(n)]
    if prefix: return prefix
    return [x for x in items if n in getattr(x, "name", "").casefold()]

def emoji(guild: discord.Guild, token: str) -> Optional[discord.Emoji]:
    if token.isdigit():
        e = discord.utils.get(guild.emojis, id=int(token))
        if e: return e
    matches = _match_by_name(guild.emojis, token)
    return sorted(matches, key=lambda x: len(x.name))[0] if matches else None

def sticker(guild: discord.Guild, token: str) -> Optional[discord.GuildSticker]:
    if token.isdigit():
        s = discord.utils.get(guild.stickers, id=int(token))
        if s: return s
    matches = _match_by_name(guild.stickers, token)
    return sorted(matches, key=lambda x: len(x.name))[0] if matches else None

def search_emojis(guild: discord.Guild, query: str) -> List[discord.Emoji]:
    q = query.casefold()
    return [e for e in guild.emojis if q in e.name.casefold()]
