# cogs/vc_name_update/member_count.py
from __future__ import annotations

import discord

def build_member_count_name(guild: discord.Guild, include_bots: bool = True) -> str:
    """
    Create the display name for the member-count voice/stage channel.
    Set include_bots=False to count only humans.
    """
    if guild is None:
        return "Members: 0"
    if include_bots:
        count = guild.member_count or len(guild.members)
    else:
        count = sum(1 for m in guild.members if not getattr(m, "bot", False))
    return f"Members: {count:,}"
