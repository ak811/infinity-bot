# cogs/nickname/service.py
from typing import Literal

import discord

from configs.config_logging import logging
from configs.config_roles import LOOT_AND_LEGENDS_ROLES  # list of (role_id, min_xp, max_xp)

from .levels import compute_level_and_next_threshold
from .formatting import (
    base_name,
    build_full_suffix,
    build_level_only_suffix,
    build_xp_only_suffix,
    build_nick_with_suffix,
    _suffix_re,  # for direct reset usage
    detect_suffix_variant_from_text,  # detect current style
)
from .constants import MAX_NICK


SuffixVariant = Literal["full", "level", "xp"]


def member_display_base(member: discord.Member) -> str:
    """Return the user's display name with any suffix stripped."""
    return base_name(member)


def _get_total_xp(user_id: int) -> int:
    """
    Lazy-imports leaderboards.main.get_total_xp to avoid circular import.
    """
    from cogs.economy.xp.service import get_total_xp as _gtx  # <-- lazy import here
    return int(_gtx(user_id))


def compute_state(member: discord.Member) -> tuple[int, int, int | None]:
    """
    Returns (xp, level, next_threshold).
    """
    xp = _get_total_xp(member.id)
    level, next_threshold = compute_level_and_next_threshold(xp, LOOT_AND_LEGENDS_ROLES)
    return xp, level, next_threshold


async def apply_suffix(member: discord.Member, variant: SuffixVariant) -> str | None:
    """
    Build the chosen suffix variant from the user's current XP/level
    and edit the nickname. Returns the new nickname if changed; else None.
    """
    xp, level, next_threshold = compute_state(member)
    base = member_display_base(member)

    if variant == "full":
        suffix = build_full_suffix(level, xp, next_threshold)
    elif variant == "level":
        suffix = build_level_only_suffix(level)
    elif variant == "xp":
        suffix = build_xp_only_suffix(xp, next_threshold)
    else:
        raise ValueError("Unknown suffix variant")

    new_nick = build_nick_with_suffix(base, suffix, MAX_NICK)
    current = member.nick if member.nick else member.name
    if current == new_nick:
        return None

    try:
        await member.edit(nick=new_nick, reason=f"Nickname {variant} suffix apply")
        logging.info(f"[nickname] Updated nick for {member.id} → {new_nick}")
        return new_nick
    except discord.Forbidden:
        logging.info(f"[nickname] Missing permissions to edit nickname for {member} (hierarchy?)")
    except discord.HTTPException as e:
        logging.info(f"[nickname] HTTPException editing nickname for {member}: {e}")

    return None


async def reset_suffix(member: discord.Member) -> str | None:
    """
    Remove any recognized suffix (full/level/xp-only).
    Returns the new nickname if changed; else None.
    """
    current = member.display_name
    cleaned = _suffix_re.sub("", current).strip()

    # If no suffix to strip, nothing to do
    if cleaned == current:
        return None

    # Reset to cleaned display_name (so effectively the base name w/out suffix)
    try:
        await member.edit(nick=cleaned, reason="Nickname suffix reset")
        logging.info(f"[nickname] Reset nick for {member.id} → {cleaned}")
        return cleaned
    except discord.Forbidden:
        logging.info(f"[nickname] Missing permissions to edit nickname for {member} (hierarchy?)")
    except discord.HTTPException as e:
        logging.info(f"[nickname] HTTPException editing nickname for {member}: {e}")

    return None


async def refresh_suffix_if_present(member: discord.Member) -> bool:
    """
    If the member already has any recognized suffix (full/level/xp-only),
    recompute from current XP and re-apply the SAME variant.
    Returns True if changed, False otherwise.
    """
    current = member.nick if member.nick else member.name
    variant = detect_suffix_variant_from_text(current)
    if not variant:
        return False

    changed = await apply_suffix(member, variant)  # uses current XP/level
    return changed is not None
