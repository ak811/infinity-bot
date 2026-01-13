# cogs/birthdays/storage.py
from __future__ import annotations
from pathlib import Path
from typing import Dict
from utils.utils_json import load_json, save_json

BIRTHDAYS_FILE = Path("database/birthdays.json")
BIRTHDAYS_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_birthdays() -> Dict[str, str]:
    return load_json(str(BIRTHDAYS_FILE))

def save_birthdays(data: Dict[str, str]) -> None:
    save_json(str(BIRTHDAYS_FILE), data)
