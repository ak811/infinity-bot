# cogs/message_stats/word_count/storage.py
from __future__ import annotations
from typing import Dict

from utils.utils_json import load_json, save_json
from configs.config_files import WORDS_FILE

def safe_load_word_counts() -> Dict[str, Dict[str, int]]:
    """Load the words file and normalize its structure to {user_id: {word: count}}."""
    data = load_json(WORDS_FILE)
    if not isinstance(data, dict):
        return {}

    normalized: Dict[str, Dict[str, int]] = {}
    for uid, bucket in data.items():
        if isinstance(bucket, dict):
            normalized[str(uid)] = {str(k): int(v) for k, v in bucket.items() if isinstance(v, (int, float))}
        elif isinstance(bucket, (int, float)):
            normalized[str(uid)] = {"__legacy_total": int(bucket)}
        else:
            normalized[str(uid)] = {}
    return normalized

def persist_word_counts(data: Dict[str, Dict[str, int]]) -> None:
    save_json(WORDS_FILE, data)
