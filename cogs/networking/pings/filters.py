# cogs/networking/pings/filters.py
from __future__ import annotations

import random
from typing import Dict, Iterable, List, Tuple

import discord

# Reuse canonical state values from storage
from .storage import (
    PING_STATE_OFF,
    PING_STATE_ON,
    PING_STATE_ONLINE_ONLY,
)

# ---------------------------
# Presence & mode helpers
# ---------------------------

def is_online_or_idle(guild: discord.Guild, user_id: int) -> bool:
    """
    True if member is Online or Idle.
    Requires Presence Intent (intents.presences=True) to be accurate.
    """
    member = guild.get_member(int(user_id))
    if not member:
        return False
    status = getattr(member, "status", None)
    return status in (discord.Status.online, discord.Status.idle)


def get_member_status_name(guild: discord.Guild, user_id: int) -> str:
    """
    Return member's presence as a string for logging.
    """
    member = guild.get_member(int(user_id))
    if not member:
        return "not_in_guild"
    status = getattr(member, "status", None)
    if status is None:
        return "unknown"
    return str(status)  # 'online', 'idle', 'dnd', 'offline'


def passes_user_mode(
    guild: discord.Guild,
    user_id: int,
    toggles: Dict[str, int],
) -> bool:
    """
    Personal mode filter:
      - 0 (off)          -> never ping
      - 1 (on)           -> always ping
      - 2 (online-only)  -> only when Online/Idle
    Defaults to ON (1) if not set.
    """
    state = toggles.get(str(user_id), PING_STATE_ON)
    if state == PING_STATE_OFF:
        return False
    if state == PING_STATE_ONLINE_ONLY:
        return is_online_or_idle(guild, user_id)
    return True

# ---------------------------
# Selection
# ---------------------------

def select_eligible_users(
    guild: discord.Guild,
    candidate_ids: Iterable[int],
    ping_toggles: Dict[str, int],
) -> Tuple[List[int], List[dict]]:
    """
    Apply personal mode + presence to candidate_ids and return:
      (eligible_user_ids, debug_rows_for_logging)

    debug_rows: [{user_id, mode, status, selected}, ...]
    """
    eligible: List[int] = []
    debug_rows: List[dict] = []

    for uid in candidate_ids:
        selected = passes_user_mode(guild, int(uid), ping_toggles)
        if selected:
            eligible.append(uid)

        mode_val = ping_toggles.get(str(uid), PING_STATE_ON)
        debug_rows.append({
            "user_id": int(uid),
            "mode": {0: "off", 1: "on", 2: "online-only"}.get(mode_val, f"unknown({mode_val})"),
            "status": get_member_status_name(guild, int(uid)),
            "selected": selected,
        })

    return eligible, debug_rows

# ---------------------------
# Mentions & ordering
# ---------------------------

def shuffled_mentions(user_ids: Iterable[int]) -> Tuple[List[int], str]:
    """
    Shuffle the provided user ids and return (shuffled_ids, mentions_string).
    """
    ids = list(user_ids)
    if not ids:
        return [], ""
    shuffled = random.sample(ids, k=len(ids))
    mentions = " ".join(f"<@{uid}>" for uid in shuffled)
    return shuffled, mentions
