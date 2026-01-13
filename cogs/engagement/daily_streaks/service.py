# cogs/daily_streaks/service.py
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

import discord

from utils.utils_json import load_json, save_json
from configs.config_channels import LOGS_CHANNEL_ID

from cogs.economy.coin.service import update_coins, get_total_coins

from configs.config_logging import logging
from configs.helper import send_as_webhook

DAILY_STREAK_FILE = "database/daily_streaks.json"

# Process-level asyncio lock for file mutations
_file_lock = asyncio.Lock()


def _bonus_for_streak(n: int) -> int:
    """
    Rolling 10-day bonuses that reset every 100 days:
    - Non-multiples of 10: 0
    - Multiples of 10: (n % 100) * 10, except when n % 100 == 0 -> 1000
    """
    if n % 10 != 0:
        return 0
    rem = n % 100
    return 1000 if rem == 0 else rem * 10


def _safe_parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        logging.warning(f"[DailyStreaks] Bad last_day in streaks file: {s!r}")
        return None


def _tz_aware_date(dt: datetime) -> datetime.date:
    """
    Convert any datetime to a UTC calendar date.
    - Naive datetimes are treated as UTC.
    - Aware datetimes are converted to UTC.
    Streak day boundaries are always 00:00–23:59 UTC.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).date()


def build_progress_bar(streak: int) -> str:
    bar_length = 7
    filled = (streak % 7) or 7
    return f"{'▰' * filled}{'▱' * (bar_length - filled)}  {filled}/{bar_length}"


async def process_daily_streak(message: discord.Message):
    """
    Backward-compatible entry point: award streaks from a Message.
    """
    if not message.guild:
        return
    await process_daily_streak_for(
        guild=message.guild,
        user=message.author,
        created_at=message.created_at or datetime.now(timezone.utc),
        post_channel_id=LOGS_CHANNEL_ID,
    )


async def process_daily_streak_for(
    guild: discord.Guild,
    user: discord.abc.User,
    created_at: Optional[datetime] = None,
    post_channel_id: Optional[int] = None,
) -> None:
    """
    Core awarder that works for any activity (message, VC, reaction).
    - Idempotent per user per day (UTC).
    - Posts a deduped embed to LOGS_CHANNEL_ID (or post_channel_id if given).
    """
    created_at = created_at or datetime.now(timezone.utc)
    today = _tz_aware_date(created_at)
    uid_str = str(user.id)

    # Serialize streak file access
    async with _file_lock:
        streaks = load_json(DAILY_STREAK_FILE, default_value={}) or {}
        user_data = streaks.get(uid_str, {"last_day": None, "streak": 0})

        last_day_dt = _safe_parse_date(user_data.get("last_day"))
        last_day = last_day_dt.date() if last_day_dt else None

        # Idempotency: already awarded today (UTC)
        if last_day == today:
            return

        # Compute new streak
        if last_day == today - timedelta(days=1):
            new_streak = int(user_data.get("streak", 0)) + 1
        else:
            new_streak = 1

        # Reward calculation
        base = ((new_streak % 7) or 7) * 10
        bonus = _bonus_for_streak(new_streak)
        total = base + bonus

        # Stage write
        prev_user_data = dict(user_data)  # rollback snapshot
        user_data.update({"last_day": today.isoformat(), "streak": new_streak})
        streaks[uid_str] = user_data

        # Write streak first
        try:
            save_json(DAILY_STREAK_FILE, streaks)
        except Exception as e:
            logging.error(f"[DailyStreaks] Failed to save streaks: {e}")
            return

    # Award coins outside the lock; rollback on failure
    try:
        update_coins(user.id, total, "Daily Streak Prize")
    except Exception as e:
        logging.error(f"[DailyStreaks] Failed to award coins, rolling back: {e}")
        async with _file_lock:
            streaks = load_json(DAILY_STREAK_FILE, default_value={}) or {}
            if uid_str in streaks:
                streaks[uid_str] = prev_user_data
                try:
                    save_json(DAILY_STREAK_FILE, streaks)
                except Exception as e2:
                    logging.error(f"[DailyStreaks] Rollback failed: {e2}")
        return

    # Success: post embed to logs (if available)
    try:
        new_coins = get_total_coins(user.id)
    except Exception:
        new_coins = None

    progress_bar = build_progress_bar(new_streak)
    bonus_msg = f"\n🎉 **Milestone! +{bonus} bonus** for {new_streak} days!" if bonus else ""

    embed = discord.Embed(
        title="📦 Daily Streak Reward!",
        description=(
            f"📅 **{getattr(user, 'display_name', getattr(user, 'name', 'User'))}**, your daily prize is here!\n\n"
            f"You're on a **{new_streak} day streak**! 🔥\n"
            f"{progress_bar}\n\n"
            f"You earned **{total} 🪙** today!{bonus_msg}\n"
            + (f"💰 Your new balance is **{new_coins} 🪙**." if new_coins is not None else "")
        ),
        color=discord.Color.green(),
    )

    channel = (
        guild.get_channel(int(post_channel_id or LOGS_CHANNEL_ID))
        if guild else None
    )
    if not channel:
        logging.info("[DailyStreaks] No logs channel available; skipping embed.")
        return

    try:
        # Mention only on day 2+
        content = f"<@{user.id}> your daily reward is here!" if new_streak >= 2 else ""
        allowed = discord.AllowedMentions(users=True, roles=False, everyone=False)
        dedupe = f"streak:{uid_str}:{today.isoformat()}"

        await send_as_webhook(
            channel,
            "daily_streak_reward",
            content=content,
            embed=embed,
            deduplication_id=dedupe,
            allowed_mentions=allowed,
        )
    except Exception as e:
        logging.error(f"[DailyStreaks] send_as_webhook failed: {e}")
