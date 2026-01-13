# cogs/economy/_shared.py
from __future__ import annotations
from typing import Dict
from utils.utils_json import load_json, save_json

CONFIRMATION_FILE = "database/confirmation_prefs.json"

def _load_confirmation_prefs() -> Dict[str, bool]:
    return load_json(CONFIRMATION_FILE, default_value={})

def is_confirmation_enabled(user_id: int) -> bool:
    data = _load_confirmation_prefs()
    return bool(data.get(str(user_id), False))

def set_confirmation(user_id: int, enabled: bool) -> None:
    data = _load_confirmation_prefs()
    data[str(user_id)] = enabled
    save_json(CONFIRMATION_FILE, data)
