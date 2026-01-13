# cogs/networking/pings/storage.py
from __future__ import annotations
from typing import Dict, Optional

from utils.utils_json import load_json, save_json
from configs.config_files import (
    PING_COUNTS_FILE,
    PING_DETAIL_FILE,
    PING_TOGGLE_FILE,
)

# Local constants (mirror of your originals)
PING_STATE_OFF = 0
PING_STATE_ON = 1
PING_STATE_ONLINE_ONLY = 2

def get_ping_mode_text(state: int) -> str:
    return {
        PING_STATE_OFF: "off 🙅",
        PING_STATE_ON: "on ✅",
        PING_STATE_ONLINE_ONLY: "online-only 🟢",
    }.get(state, "on ✅")

def get_user_ping_state(user_id: int) -> int:
    data: Dict[str, int] = load_json(PING_TOGGLE_FILE, default_value={})
    state = data.get(str(user_id))
    if state in (PING_STATE_OFF, PING_STATE_ON, PING_STATE_ONLINE_ONLY):
        return state
    return PING_STATE_ON  # default

def set_user_ping_state(user_id: int, state: int) -> None:
    data: Dict[str, int] = load_json(PING_TOGGLE_FILE, default_value={})
    data[str(user_id)] = state
    save_json(PING_TOGGLE_FILE, data)

def load_ping_counts() -> Dict[str, int]:
    return load_json(PING_COUNTS_FILE, default_value={})

def load_ping_detail() -> Dict[str, Dict[str, int]]:
    return load_json(PING_DETAIL_FILE, default_value={})

def load_ping_toggles() -> Dict[str, int]:
    """
    Bulk-load the per-user ping mode map expected by filters.select_eligible_users.
    Keys are user ids as strings; values are ints (0/1/2).
    """
    return load_json(PING_TOGGLE_FILE, default_value={})
