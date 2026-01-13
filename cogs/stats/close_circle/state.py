# cogs/close_circle/state.py
import os
from collections import defaultdict

# === Persistent data file ===
DATA_FILE = "database/close_circle_data.json"

# === Runtime state ===
# Interaction scoring: giver_id -> receiver_id -> score
interaction_scores = defaultdict(lambda: defaultdict(int))

# Message proximity: channel_id -> last author (discord.Member – set at runtime)
previous_message_user = {}

# Emoji reaction history: uid -> uid -> set(emoji)
reaction_history = defaultdict(lambda: defaultdict(set))

# Voice tracking: member_id -> datetime (UTC)
vc_join_times = {}

# Alias & derived
given_scores = interaction_scores
received_scores = defaultdict(lambda: defaultdict(int))  # built from interaction_scores

# Ensure the storage directory exists
_dir = os.path.dirname(DATA_FILE)
if _dir and not os.path.exists(_dir):
    os.makedirs(_dir, exist_ok=True)
