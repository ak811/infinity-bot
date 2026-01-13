# cogs/xp/weights.py
# Default activity weights used to compute total score from per-activity tallies.
# Add or override freely. Missing keys default to weight 1.0.

ACTIVITY_WEIGHTS = {
    "messages": 1.0,
    "reactions:add": 1.0,
    "reactions:receive": 1.0,

    # Voice is tracked as seconds; 1 XP per minute:
    "vc_seconds": 1.0 / 60.0,

    # Unique-user reaction gates (if you track these)
    "add_reaction": 1.0,
    "receive_reaction": 1.0,

    # Custom buckets you already use
    "bump": 1.0,
    "tree": 1.0,
    "message length": 1.0,
    "message_length": 1.0,
    "link/media": 1.0,
}
