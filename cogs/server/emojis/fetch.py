# cogs/server/emojis/fetch.py
from __future__ import annotations
import discord
from typing import List
from . import cache, constants
from .errors import IntentsMissingError

def _assert_intents(guild: discord.Guild) -> None:
    if not guild.me or not guild._state._intents.emojis_and_stickers:  # type: ignore
        raise IntentsMissingError()

def get_emojis(guild: discord.Guild) -> List[discord.Emoji]:
    _assert_intents(guild)
    key = cache.make_key("emojis", guild.id)
    return cache.get_or_set(key, constants.TTL_EMOJIS, lambda: list(guild.emojis))

def get_stickers(guild: discord.Guild) -> List[discord.GuildSticker]:
    _assert_intents(guild)
    key = cache.make_key("stickers", guild.id)
    return cache.get_or_set(key, constants.TTL_STICKERS, lambda: list(guild.stickers))
