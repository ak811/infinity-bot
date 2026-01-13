# cogs/server/emojis/commands_stickers.py
from __future__ import annotations
import discord
from typing import List

from .fetch import get_stickers
from .builders import make_sticker_single_pages
from .constants import STICKERS_TITLE

def build_stickers_list(guild: discord.Guild) -> List[discord.Embed]:
    """
    Return pages where each page is a single embed showing one sticker image.
    """
    data = get_stickers(guild)
    return make_sticker_single_pages(STICKERS_TITLE, data)
