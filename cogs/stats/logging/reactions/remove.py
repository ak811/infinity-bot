# cogs/stats/logging/reactions/remove.py
from __future__ import annotations
from discord import RawReactionActionEvent

def emoji_key_from_payload(payload: RawReactionActionEvent) -> str:
    """
    Canonical key for mapping lookups:
      - Custom emoji -> f"custom:{id}"
      - Unicode emoji -> f"uni:{name}"
    """
    if payload.emoji.id:
        return f"custom:{payload.emoji.id}"
    return f"uni:{payload.emoji.name or ''}"
