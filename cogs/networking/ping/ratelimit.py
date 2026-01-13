# cogs/ping/ratelimit.py
from __future__ import annotations
import time

from .config import PER_USER_COOLDOWN, PER_ROLE_COOLDOWN

# In-memory cooldown buckets: {(guild_id, user_id): timestamp}
_user_cd: dict[tuple[int, int], float] = {}
_role_cd: dict[tuple[int, int], float] = {}

def _remaining(ts: float, cooldown: int) -> int:
    now = time.time()
    left = int((ts + cooldown) - now)
    return max(0, left)

def check_user_cooldown(guild_id: int, user_id: int) -> int:
    key = (guild_id, user_id)
    ts = _user_cd.get(key, 0.0)
    return _remaining(ts, PER_USER_COOLDOWN) if ts else 0

def stamp_user_cooldown(guild_id: int, user_id: int) -> None:
    _user_cd[(guild_id, user_id)] = time.time()

def check_role_cooldown(guild_id: int, role_id: int) -> int:
    key = (guild_id, role_id)
    ts = _role_cd.get(key, 0.0)
    return _remaining(ts, PER_ROLE_COOLDOWN) if ts else 0

def stamp_role_cooldown(guild_id: int, role_id: int) -> None:
    _role_cd[(guild_id, role_id)] = time.time()
