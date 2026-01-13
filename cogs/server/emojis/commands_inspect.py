# cogs/server/emojis/commands_inspect.py
from __future__ import annotations
import discord
from typing import List

from .resolve import emoji as resolve_emoji, sticker as resolve_sticker, search_emojis
from .builders import make_emoji_detail, make_sticker_detail, make_paged_group_list_embeds
from .constants import EMOJIS_TITLE
from .categorize import emojis as categorize_emojis

def build_emoji_detail(guild: discord.Guild, token: str) -> discord.Embed | None:
    it = resolve_emoji(guild, token)
    return make_emoji_detail(it) if it else None

def build_sticker_detail(guild: discord.Guild, token: str) -> discord.Embed | None:
    it = resolve_sticker(guild, token)
    return make_sticker_detail(it) if it else None

def build_emoji_search(guild: discord.Guild, query: str) -> List[discord.Embed]:
    results = search_emojis(guild, query)
    groups = categorize_emojis(results)
    if not groups:
        groups = {"🔎 Search Results": []}
    # Title includes the query
    return make_paged_group_list_embeds(f"🔎 Emojis matching “{query}”", groups)
