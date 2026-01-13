# cogs/server/emojis/commands_emojis.py
from __future__ import annotations
import discord
from typing import List, Dict

from .fetch import get_emojis
from .categorize import emojis as categorize_emojis

def _groups_to_text_pages(groups: Dict[str, List[str]], *, per_line: int = 5, lines_per_page: int = 5) -> List[str]:
    """
    Convert grouped emoji rows (strings like '<:name:id>' with optional 🔒)
    into content-only pages that render as jumbo emojis:
      - Each line contains up to `per_line` emoji tokens.
      - Each page contains exactly up to `lines_per_page` lines.
    NOTE: We intentionally keep lines as ONLY emojis and spaces to preserve jumbo emoji size.
    """
    # 1) Pack each category into fixed-width lines
    lines: List[str] = []
    for _, rows in groups.items():
        for i in range(0, len(rows), per_line):
            # A line is ONLY emojis & spaces → jumbo emoji rendering.
            line = " ".join(rows[i:i + per_line])
            if line.strip():
                lines.append(line)

    if not lines:
        return [""]

    # 2) Chunk lines into pages
    pages: List[str] = []
    for i in range(0, len(lines), lines_per_page):
        page_lines = lines[i:i + lines_per_page]
        pages.append("\n".join(page_lines))
    return pages

def build_emojis_pages_text(guild: discord.Guild, *, per_line: int = 5, lines_per_page: int = 5) -> List[str]:
    """
    Build content-only pages for emojis. These pages are meant to be sent as `content=...`
    (no embeds) so that Discord displays the emojis in big (jumbo) size.
    """
    data = get_emojis(guild)
    groups = categorize_emojis(data)  # category -> list of emoji_row strings
    return _groups_to_text_pages(groups, per_line=per_line, lines_per_page=lines_per_page)
