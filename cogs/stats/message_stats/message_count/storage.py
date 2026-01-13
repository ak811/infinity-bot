# cogs/message_stats/message_count/storage.py
from __future__ import annotations
from typing import Dict
from utils.utils_json import load_json, save_json
from configs.config_files import MESSAGE_LEADERBOARD_FILE

def load_counts() -> Dict[str, int]:
    return load_json(MESSAGE_LEADERBOARD_FILE, default_value={})

def save_counts(data: Dict[str, int]) -> None:
    save_json(MESSAGE_LEADERBOARD_FILE, data)

def increment_user_message_count(user_id: int) -> None:
    data = load_counts()
    key = str(user_id)
    data[key] = data.get(key, 0) + 1
    save_counts(data)
