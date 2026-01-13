# cogs/server/channels/archive_config.py
from datetime import timezone, time

# Archive category selection (ID preferred if set; else falls back to NAME)
ARCHIVE_CATEGORY_ID: int = 1431555448917725184
ARCHIVE_CATEGORY_NAME: str = "Archive"

# Behavior
INACTIVITY_DAYS = 7
SWEEP_UTC_TIME = time(hour=4, tzinfo=timezone.utc)  # daily sweep time (UTC)
ARCHIVE_TEXT = True
ARCHIVE_VOICE = True
REQUIRE_PUBLIC = True                # only affect channels visible to @everyone
PINNED_CHANNEL_IDS: set[int] = set() # never archive these channel IDs

# Exclusions
EXCLUDED_CATEGORY_IDS: set[int] = set({1411930990359871589, 1171460837773410314})  # e.g., {123456789012345678}
EXCLUDED_CHANNEL_IDS: set[int] = set({1431397590343352350, 1415896576534122557, 1422745741784256564, 1412689888876433439, 1382463998150316084})   # e.g., {234567890123456789}

# NEW: For voice channels, require recent MESSAGE activity to count as "active".
# If True: VC is active only if it has a recent message (within INACTIVITY_DAYS) or is currently occupied.
# If False: VC is active if it has either recent voice presence OR a recent message, or is currently occupied.
VC_REQUIRE_RECENT_MESSAGE: bool = True

# Optional: custom directory for JSON persistence (None = next to this package)
DATA_DIR: str | None = None
