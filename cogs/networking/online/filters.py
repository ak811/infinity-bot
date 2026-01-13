# cogs/online/filters.py
from __future__ import annotations

import discord

from configs.config_roles import LOOT_AND_LEGENDS_ROLES, CONTRIBUTOR_ROLE_ID

# Allowed role IDs (first elem in each tuple) + contributor
ALLOWED_ROLE_IDS: set[int] = {int(role_id) for (role_id, *_rest) in LOOT_AND_LEGENDS_ROLES}
ALLOWED_ROLE_IDS.add(int(CONTRIBUTOR_ROLE_ID))

OFFLINE_STATES: set[discord.Status] = {
    discord.Status.offline,
    getattr(discord.Status, "invisible", discord.Status.offline),
}
ONLINE_DEST_STATES: set[discord.Status] = {
    discord.Status.online,
    discord.Status.idle,
    discord.Status.dnd,
}

def has_allowed_role(member: discord.Member) -> bool:
    return any(
        isinstance(r, discord.Role) and r.id in ALLOWED_ROLE_IDS
        for r in getattr(member, "roles", [])
    )
