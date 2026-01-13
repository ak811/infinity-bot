# cogs/server/emojis/events.py
from __future__ import annotations
import discord
from . import cache

def on_emojis_update(guild: discord.Guild) -> None:
    cache.invalidate("emojis", guild.id)

def on_stickers_update(guild: discord.Guild) -> None:
    cache.invalidate("stickers", guild.id)
