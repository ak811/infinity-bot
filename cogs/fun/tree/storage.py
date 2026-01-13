# cogs/tree/storage.py
from __future__ import annotations
from typing import Any, Dict, Optional
from utils.utils_json import load_json, save_json
from pathlib import Path

# Files (same paths you used)
LAST_ORB_RECEIVER_FILE = "database/last_orb_receiver.json"  # kept separate from config file to avoid confusion
LAST_PING_TIMESTAMP_FILE = "database/last_ping_timestamp.json"
PING_FILE_PATH = "database/ping_roles.json"

# Backward compatibility: your original code stored last_orb_receiver in configs.config_files.LAST_ORB_RECEIVER_FILE
# If you want to keep that exact path, change LAST_ORB_RECEIVER_FILE above to the same value.

Path("database").mkdir(parents=True, exist_ok=True)

def load_last_orb_receiver(default: Optional[int] = None) -> Optional[int]:
    data: Dict[str, Any] = load_json(LAST_ORB_RECEIVER_FILE, {"last_orb_receiver": default})
    return data.get("last_orb_receiver", default)

def save_last_orb_receiver(user_id: Optional[int]) -> None:
    save_json(LAST_ORB_RECEIVER_FILE, {"last_orb_receiver": user_id})

def load_last_ping_timestamp(default: Optional[int] = None) -> Optional[int]:
    data: Dict[str, Any] = load_json(LAST_PING_TIMESTAMP_FILE, {"last_ping_timestamp": default})
    return data.get("last_ping_timestamp", default)

def save_last_ping_timestamp(ts: Optional[int]) -> None:
    save_json(LAST_PING_TIMESTAMP_FILE, {"last_ping_timestamp": ts})

def load_ping_roles() -> Dict[str, list[int]]:
    return load_json(PING_FILE_PATH, {})
