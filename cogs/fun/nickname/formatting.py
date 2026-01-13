# cogs/nickname/formatting.py
import re
import discord
from .constants import MAX_NICK

# Matches any of these at the end of the name:
# 1) " | L6 • 309/500 XP"  (full)
# 2) " | L6"               (level-only)
# 3) " | 309/500 XP"       (xp-only)
# 4) Handles max-tier XP (no /next)
_suffix_re = re.compile(
    r"(?:\s*\|\s*(?:L\d+(?:\s*•\s*\d+(?:/\d+)?\s*XP)?|\d+(?:/\d+)?\s*XP))\s*$"
)

def base_name(member: discord.Member) -> str:
    """
    Returns the member's current display name (nick if set, else username),
    with any XP/level suffix stripped.
    """
    current = member.display_name
    return _suffix_re.sub("", current).strip()

def build_full_suffix(level: int, xp: int, next_threshold: int | None) -> str:
    if next_threshold is not None:
        return f" | L{level} • {xp}/{next_threshold} XP"
    return f" | L{level} • {xp} XP"

def build_level_only_suffix(level: int) -> str:
    return f" | L{level}"

def build_xp_only_suffix(xp: int, next_threshold: int | None) -> str:
    if next_threshold is not None:
        return f" | {xp}/{next_threshold} XP"
    return f" | {xp} XP"

def build_nick_with_suffix(base: str, suffix: str, max_len: int = MAX_NICK) -> str:
    """
    Combines base + suffix respecting Discord's limit, truncating base and
    preserving an ellipsis where possible. Returns a string <= max_len.
    """
    space_left = max_len - len(suffix)
    if space_left <= 0:
        # Fallback: if literally no room for base, return trimmed suffix without leading space.
        return suffix.strip()[:max_len]

    # Truncate base if needed
    if len(base) > space_left:
        if space_left >= 2:
            base = base[:space_left - 1] + "…"
        else:
            base = base[:space_left]

    return (base + suffix)[:max_len]


# NEW: detect which variant is present (so we can refresh the SAME style)
def detect_suffix_variant_from_text(text: str) -> str | None:
    """
    Returns 'full' | 'level' | 'xp' if a known suffix variant is present, else None.
    Priority matters: check FULL first to avoid matching level-only inside full.
    """
    full_pat  = re.compile(r"\s*\|\s*L\d+\s*•\s*\d+(?:/\d+)?\s*XP\s*$")
    level_pat = re.compile(r"\s*\|\s*L\d+\s*$")
    xp_pat    = re.compile(r"\s*\|\s*\d+(?:/\d+)?\s*XP\s*$")

    if full_pat.search(text):
        return "full"
    if level_pat.search(text):
        return "level"
    if xp_pat.search(text):
        return "xp"
    return None
