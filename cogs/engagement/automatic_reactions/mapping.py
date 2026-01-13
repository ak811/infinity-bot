# cogs/automatic_reactions/mapping.py
from __future__ import annotations
from typing import Dict, Iterable, List, Tuple, Set, Optional
import configs.config_channels as ch  # import the module so we can getattr safely

# Author ID with the special sloth reaction in the “nice” channels
SLOTH_USER_ID = 919849745705472051

def _resolve_ids(names: Iterable[str]) -> List[int]:
    """
    Resolve channel id constant names from configs.config_channels.
    Silently drops missing/typo'd names to avoid crashes.
    """
    ids: List[int] = []
    for name in names:
        val = getattr(ch, name, None)
        if isinstance(val, int):
            ids.append(val)
    return ids

# --- Define channel groups by constant NAME (strings). ---
WELCOME = _resolve_ids([
    "WELCOME_CHANNEL_ID",
    "INTRODUCE_YOURSELF_CHANNEL_ID",
])

NICE = _resolve_ids([
    "SELFIES_CHANNEL_ID",
])

REVIEW = _resolve_ids([
    "SERVER_SUGGESTIONS_CHANNEL_ID",
])

LAUGH = _resolve_ids([
    "MEMES_MEDIA_CHANNEL_ID",
    "FUN_FACTS_CHANNEL_ID",
])

SPARKLING = _resolve_ids([
    "MUSIC_SPOTIFY_CHANNEL_ID",
    "LINKS_MEDIA_CHANNEL_ID",
    "POSITIVE_VIBE_CHANNEL_ID",
    "PHOTOGRAPHY_CHANNEL_ID",
    "AI_GENERATED_CHANNEL_ID",
    "BUMP_US_CHANNEL_ID",
    "QUOTES_CHANNEL_ID",
    "POEMS_CHANNEL_ID",
    "POLLS_CHANNEL_ID",
    "SERVER_UPDATES_CHANNEL_ID",
    "SING_SING_CHANNEL_ID",
    "HIGHLIGHT_OF_THE_DAY_CHANNEL_ID",
    "MEMORIES_CHANNEL_ID",
    # These two had typos in the original snippet; resolve them if defined:
    "ADHD_TOUGHTS_CHANNEL_ID",   # keep as-is (typo) to match config if it exists
    "INTERNET_PICS",             # if your config uses *_ID, add the correct name there
    "EVENTS_CHANNEL_ID",
    "ANNOUNCEMENTS_CHANNEL_ID",
    "NEWS_CHANNEL_ID"
])

FOOD = _resolve_ids([
    "FOOD_CHANNEL_ID",
])

CHECKMARK = _resolve_ids([
    "BOT_PLAYGROUND_CHANNEL_ID",
    "SUGGEST_A_WORD_CHANNEL_ID"
])

THUMBS_MAG = _resolve_ids([
    "SUGGESTIONS_CHANNNEL_ID",  # triple-n in original; resolve if present
])

# --- Map each group of channel IDs to its emoji list. ---
# Lists are templates; the cog will copy them per-use so we never mutate these globals.
REACTION_MAP: Dict[Tuple[int, ...], List[str]] = {
    tuple(WELCOME):   ['👋🏼', '✨'],
    tuple(NICE):      ['✨', '🔥', '😻'],
    tuple(REVIEW):    ['🔍'],
    tuple(LAUGH):     ['😂', '👀', '🤣'],
    tuple(SPARKLING): ['✨'],
    tuple(FOOD):      ['✨', '😋'],
    tuple(CHECKMARK): ['✅'],
    tuple(THUMBS_MAG): ['⬆️', '⬇️', '🔍'],
}
