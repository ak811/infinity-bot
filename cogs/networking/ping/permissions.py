# cogs/ping/permissions.py
from __future__ import annotations
import discord
from typing import Optional

from cogs.server.roles.rank import get_highest_loot_legends_role_index
from configs.config_roles import LOOT_AND_LEGENDS_ROLES
from .config import ELITE_MIN_INDEX, PING_ALLOWED_CHANNEL_IDS, PINGABLE_EXTRA_ROLE_IDS

def is_elite_plus(member: discord.Member) -> bool:
    try:
        idx = get_highest_loot_legends_role_index(member)
        return idx >= ELITE_MIN_INDEX
    except Exception:
        return False

def role_ladder_index(role: discord.Role) -> int:
    for i, (rid, *_rest) in enumerate(LOOT_AND_LEGENDS_ROLES):
        if role.id == rid:
            return i
    return -1

def is_pingable_elite_plus(role: discord.Role) -> bool:
    # Whitelist wins first
    if role.id in PINGABLE_EXTRA_ROLE_IDS:
        return True
    # Otherwise: must be Elite+ ladder role
    idx = role_ladder_index(role)
    return idx >= ELITE_MIN_INDEX

async def can_use_here(ctx) -> bool:
    if not PING_ALLOWED_CHANNEL_IDS:
        return True
    return ctx.channel.id in PING_ALLOWED_CHANNEL_IDS
