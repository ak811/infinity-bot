# cogs/message_stats/pings_count/storage.py
from __future__ import annotations
from typing import Dict

from utils.utils_json import load_json, save_json
from configs.config_files import PING_COUNTS_FILE, PING_DETAIL_FILE

def load_counts() -> Dict[str, int]:
    return load_json(PING_COUNTS_FILE, default_value={})

def save_counts(data: Dict[str, int]) -> None:
    save_json(PING_COUNTS_FILE, data)

def load_detail() -> Dict[str, Dict[str, int]]:
    return load_json(PING_DETAIL_FILE, default_value={})

def save_detail(data: Dict[str, Dict[str, int]]) -> None:
    save_json(PING_DETAIL_FILE, data)
