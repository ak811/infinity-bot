# cogs/welcome/helpers.py
from __future__ import annotations

import discord
from typing import Iterable

from configs.config_roles import LOOT_AND_LEGENDS_ROLES

def member_has_loot_legends_role(member: discord.Member) -> bool:
    """
    Returns True if the member already has any Loot & Legends role.
    LOOT_AND_LEGENDS_ROLES is expected to be an iterable of tuples like:
      (role_id, min_xp, display_name)  # only the first element is used here
    """
    ll_role_ids = {int(role_id) for (role_id, *_rest) in LOOT_AND_LEGENDS_ROLES}
    return any(getattr(r, "id", 0) in ll_role_ids for r in getattr(member, "roles", ()))
