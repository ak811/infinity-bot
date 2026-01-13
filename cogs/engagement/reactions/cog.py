# cogs/engagement/reactions/cog.py
from __future__ import annotations
import json
from pathlib import Path
import asyncio
import datetime as dt
import discord
from discord.ext import commands

from configs.config_logging import logging
from configs.config_general import COIN_EMOJI, ORB_EMOJI, STAR_EMOJI, FORWARD_EMOJI
from configs.config_channels import JUDGE_ZONE_CHANNEL_ID

from cogs.economy.xp.service import update_xp

from .utils import (
    normalize_emoji,
    fetch_message_or_none,
    track_reaction_counts_and_details,
    count_user_reacts_on_message,
)
from .forwards import forward_message_to_dm
from .donations import handle_donation_reaction, ignored_reactions
from .viral import handle_viral_post_check


# ------------------------------
# Reactions XP daily cap storage
# ------------------------------

DATA_DIR = Path("database")
DATA_DIR.mkdir(parents=True, exist_ok=True)
REACTIONS_LIMITS_FILE = DATA_DIR / "reactions_limits.json"
REACTIONS_DAILY_CAP = 100  # max XP gained per user per day (from reactions)

# { "<user_id>": { "date": "YYYY-MM-DD", "gained": float } }
_reactions_limits_lock = asyncio.Lock()

def _today_str() -> str:
    # Use system local date; if you prefer a specific TZ, adjust here.
    return dt.date.today().isoformat()

def _load_reactions_limits() -> dict[str, dict[str, float | str]]:
    try:
        with REACTIONS_LIMITS_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logging.warning(f"[ReactionsCap] Failed to load limits: {e}")
        return {}

def _save_reactions_limits_sync(data: dict[str, dict[str, float | str]]) -> None:
    tmp = REACTIONS_LIMITS_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    tmp.replace(REACTIONS_LIMITS_FILE)

async def _save_reactions_limits(data: dict[str, dict[str, float | str]]) -> None:
    async with _reactions_limits_lock:
        _save_reactions_limits_sync(data)

def _ensure_fresh_record(rec: dict[str, float | str]) -> dict[str, float | str]:
    today = _today_str()
    if rec.get("date") != today:
        return {"date": today, "gained": 0.0}
    return rec

def _get_remaining_gain(rec: dict[str, float | str]) -> int:
    gained = float(rec.get("gained", 0.0))
    remaining = max(0, REACTIONS_DAILY_CAP - int(gained))
    return remaining

async def award_reaction_xp_with_daily_cap(user_id: int | str, delta: int, reason: str) -> None:
    """
    Cap only positive deltas toward REACTIONS_DAILY_CAP per user/day (tracked as 'gained').
    Negative deltas (loss) are always applied and do NOT reduce the 'gained' counter.
    """
    # Normalize to string for JSON keys
    uid = str(user_id)

    if delta == 0:
        return

    # Fast path: deductions are never capped
    if delta < 0:
        update_xp(uid, delta, reason)
        return

    # Positive delta: cap by remaining
    limits = _load_reactions_limits()
    rec = _ensure_fresh_record(limits.get(uid, {}))
    remaining = _get_remaining_gain(rec)

    applied = min(delta, remaining)
    if applied <= 0:
        logging.debug(f"[ReactionsCap] {uid} at cap ({REACTIONS_DAILY_CAP}); skipping +XP")
        return

    # Apply XP and bump 'gained'
    update_xp(uid, applied, reason)
    rec["gained"] = float(rec.get("gained", 0.0)) + applied
    limits[uid] = rec
    await _save_reactions_limits(limits)


class ReactionsCog(commands.Cog):
    """Handle raw reaction add/remove: forwarding, donations, viral, XP tracking (with daily cap)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel) or channel.id == JUDGE_ZONE_CHANNEL_ID:
            return

        message = await fetch_message_or_none(channel, payload.message_id)
        if not message:
            return

        emoji_str = normalize_emoji(payload.emoji)
        logging.info(f"[RawAdd] emoji={emoji_str} by {payload.user_id} on message {payload.message_id}")

        # 1) Forward-to-DM
        if emoji_str == FORWARD_EMOJI:
            await forward_message_to_dm(payload, message, self.bot)
            return

        # 2) Donations
        if emoji_str in (COIN_EMOJI, ORB_EMOJI, STAR_EMOJI):
            await handle_donation_reaction(payload, message, self.bot, emoji_str, action="add")
            return

        # 3) Viral post check (fire-and-forget)
        await handle_viral_post_check(self.bot, payload)

        # 4) Normal reaction tracking (skip bot-authored messages entirely)
        if not message.author or message.author.bot:
            return

        await track_reaction_counts_and_details(message, payload.user_id, emoji_str)

        # 5) Unique-user XP gating
        try:
            total_reacts_by_user = await count_user_reacts_on_message(message, payload.user_id)
        except Exception as e:
            logging.warning(f"[RawAdd] Failed counting user reacts: {e}")
            total_reacts_by_user = None

        if total_reacts_by_user == 1:
            # Apply daily-capped XP for both author (receive) and reactor (add)
            await award_reaction_xp_with_daily_cap(message.author.id, 1, "receive_reaction")
            await award_reaction_xp_with_daily_cap(payload.user_id, 1, "add_reaction")

    @commands.Cog.listener("on_raw_reaction_remove")
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return

        emoji_str = normalize_emoji(payload.emoji)
        key = (payload.message_id, payload.user_id, emoji_str)

        # Handle ignored removals (e.g., after we programmatically removed a reaction)
        if key in ignored_reactions:
            logging.info(f"[RawRemove] Ignored removal for key: {key}")
            ignored_reactions.discard(key)
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel) or channel.id == JUDGE_ZONE_CHANNEL_ID:
            return

        message = await fetch_message_or_none(channel, payload.message_id)
        if not message:
            return

        logging.info(f"[RawRemove] emoji={emoji_str} by {payload.user_id} on message {payload.message_id}")

        # Donation removals
        if emoji_str in (COIN_EMOJI, ORB_EMOJI, STAR_EMOJI):
            await handle_donation_reaction(payload, message, self.bot, emoji_str, action="remove")

        # Never adjust XP on bot-authored messages
        if not message.author or message.author.bot:
            return

        # Unique-user XP gating (stateless)
        try:
            total_reacts_by_user = await count_user_reacts_on_message(message, payload.user_id)
        except Exception as e:
            logging.warning(f"[RawRemove] Failed counting user reacts: {e}")
            total_reacts_by_user = None

        # Mirror your rule: don't deduct if reactor is the author
        if total_reacts_by_user == 0 and payload.user_id != message.author.id:
            # Negative deltas are not capped and do not reduce the 'gained' tally
            await award_reaction_xp_with_daily_cap(message.author.id, -1, "receive_reaction")
            await award_reaction_xp_with_daily_cap(payload.user_id, -1, "add_reaction")


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionsCog(bot))
