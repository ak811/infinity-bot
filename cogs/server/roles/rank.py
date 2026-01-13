from __future__ import annotations
import discord
from configs.config_roles import LOOT_AND_LEGENDS_ROLES

def get_highest_loot_legends_role_index(member: discord.Member) -> int:
    member_ids = {r.id for r in member.roles}
    hi = -1
    for i, (rid, *_rest) in enumerate(LOOT_AND_LEGENDS_ROLES):
        if rid in member_ids and i > hi:
            hi = i
    return hi
