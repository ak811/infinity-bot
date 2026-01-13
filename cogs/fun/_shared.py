# cogs/fun/_shared.py
from __future__ import annotations

import random
from pathlib import Path
from typing import List
from utils.utils_json import load_json
from configs.config_logging import logging

DATA_DIR = Path("database")
FORTUNE_PATH = DATA_DIR / "fortune.json"
TOPICS_PATH = DATA_DIR / "topics.json"
COMPLIMENTS_PATH = DATA_DIR / "compliments.json"

def safe_random_from_json(path: Path, fallback: List[str], label: str) -> str:
    """Load a list from JSON and return a random entry; fallback if invalid/empty."""
    try:
        data = load_json(str(path))
        if isinstance(data, list) and data and all(isinstance(x, str) for x in data):
            return random.choice(data)
        logging.warning(f"[{label}] {path} is empty/invalid; using fallback.")
    except Exception as e:
        logging.exception(f"[{label}] Failed to load {path}: {e}")
    return random.choice(fallback)
