# cogs/ping/config.py
from __future__ import annotations

# === Thresholds / Tunables ====================================================
# Elite is index 4 in your ladder. Anyone with highest index >= 4 is Elite+.
ELITE_MIN_INDEX: int = 4

# Channel gating (reuse your bots playground; make empty list to allow anywhere)
try:
    PING_ALLOWED_CHANNEL_IDS = []
except Exception:
    PING_ALLOWED_CHANNEL_IDS = []

# Cooldowns (seconds)
PER_USER_COOLDOWN: int = 300
PER_ROLE_COOLDOWN: int = 120

# Message limits
MAX_PING_SIZE: int = 5000
ALLOW_OPTIONAL_MESSAGE: bool = True

# Extra roles (outside the ladder) that are allowed to be pinged
try:
    from configs.config_roles import (
        BOOK_CLUB_ROLE,
        CHILL_AND_LEARN_ROLE,
        GAMING_CLUB_ROLE,
        # add more here...
    )
    PINGABLE_EXTRA_ROLE_IDS: set[int] = {
        BOOK_CLUB_ROLE,
        CHILL_AND_LEARN_ROLE,
        GAMING_CLUB_ROLE,
    }
except Exception:
    PINGABLE_EXTRA_ROLE_IDS: set[int] = set()