# cogs/misc/disboard/cog.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks

from utils.utils_json import load_json
from configs.helper import send_as_webhook
from configs.config_channels import BUMP_US_CHANNEL_ID

from cogs.networking.pings.filters import select_eligible_users, shuffled_mentions
from cogs.networking.pings.storage import load_ping_toggles

from cogs.economy.orb.service import update_orbs

from cogs.economy.xp.service import update_xp

from .logic import (
    find_latest_bump_message,
    build_generic_reminder,
    identify_bumper_user_with_source,
)

REMINDER_COOLDOWN = timedelta(hours=2)

# Primary “fresh” window for instant awards.
AWARD_WINDOW_SECONDS = 180

# If we missed the fresh window (restarts, hiccups), still award once
# within this larger window, provided we haven't already awarded for that message_id.
RETRO_AWARD_WINDOW_SECONDS = 1800  # 30 minutes

PING_FILE_PATH = "database/ping_roles.json"

# Persistent award state (avoid double-award across restarts)
AWARD_STATE_PATH = Path("database/disboard_awards.json")


def _load_award_state() -> set[int]:
    try:
        if AWARD_STATE_PATH.exists():
            data = json.loads(AWARD_STATE_PATH.read_text(encoding="utf-8") or "{}")
            ids = set(int(x) for x in data.get("awarded_message_ids", []))
            logging.debug("[Disboard] 💾 Loaded award state: %d ids", len(ids))
            return ids
    except Exception as e:
        logging.error("[Disboard] 💥 Failed to load award state: %r", e, exc_info=True)
    return set()


def _save_award_state(awarded_ids: set[int]) -> None:
    try:
        AWARD_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        payload = {"awarded_message_ids": list(awarded_ids)}
        AWARD_STATE_PATH.write_text(json.dumps(payload), encoding="utf-8")
        logging.debug("[Disboard] 💾 Saved award state: %d ids", len(awarded_ids))
    except Exception as e:
        logging.error("[Disboard] 💥 Failed to save award state: %r", e, exc_info=True)


class DisboardCog(commands.Cog):
    """
    Watches the bump channel for DISBOARD confirmations, awards orbs,
    and schedules/reminds after the 2h cooldown.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_reminded_bump_id: int | None = None
        # in-memory + persisted set of message IDs we already awarded for
        self._awarded_ids: set[int] = _load_award_state()
        self.monitor_loop.start()

    async def cog_unload(self):
        self.monitor_loop.cancel()

    async def _maybe_award(self, *, bump_message: discord.Message, age_secs: int) -> None:
        """
        Award orbs/xp if within fresh or retro window and not already awarded.
        """
        msg_id = int(getattr(bump_message, "id", 0) or 0)
        if not msg_id:
            logging.warning("[Disboard] 🆔 Missing message id; skipping award.")
            return

        # Decide which window applies
        fresh = age_secs <= AWARD_WINDOW_SECONDS
        retro = (AWARD_WINDOW_SECONDS < age_secs <= RETRO_AWARD_WINDOW_SECONDS)

        if not (fresh or retro):
            logging.debug(
                "[Disboard] ⏭️ Skipping award completely: age_secs=%d > retro_window=%d",
                age_secs, RETRO_AWARD_WINDOW_SECONDS
            )
            return

        if msg_id in self._awarded_ids:
            logging.info(
                "[Disboard] 🔁 Not awarding again (already awarded): message_id=%s age_secs=%d",
                msg_id, age_secs
            )
            return

        try:
            user, source = identify_bumper_user_with_source(bump_message)
            logging.info(
                "[Disboard] 🎯 Award path: fresh=%s retro=%s window_fresh=%d window_retro=%d "
                "mentions=%d has_interaction=%s user_found=%s source=%s",
                fresh, retro, AWARD_WINDOW_SECONDS, RETRO_AWARD_WINDOW_SECONDS,
                len(bump_message.mentions),
                bool(getattr(bump_message, "interaction", None)),
                bool(user), source,
            )
            if not user:
                logging.warning(
                    "[Disboard] ⚠️ Could not identify who bumped "
                    "(no interaction.user, no message mentions, no embed mention)."
                )
                return

            update_orbs(user.id, 1, "bump")
            update_xp(user.id, 10, "bump")

            display = getattr(user, "display_name", getattr(user, "name", str(user.id)))
            embed = discord.Embed(
                title="🎉 Bump Successful!",
                description=(
                    f"Thanks, {user.mention} `{display}`!\n"
                    f"I'll remind you again in **2 hours** ⏰\n"
                    f"🔮 You earned **1 Orb** for bump!"
                ),
                color=discord.Color.purple(),
            )
            channel = bump_message.channel
            if isinstance(channel, discord.TextChannel):
                # include timing context in the footer for transparency
                footer = f"awarded via {'fresh' if fresh else 'retro'} window at {datetime.now(timezone.utc).isoformat()}"
                embed.set_footer(text=footer)
                await send_as_webhook(channel, "disboard", embed=embed)

            self._awarded_ids.add(msg_id)
            _save_award_state(self._awarded_ids)

            logging.info(
                "[Disboard] ✅ Orb/Xp awarded: user_id=%s display='%s' source=%s message_id=%s age_secs=%d mode=%s",
                user.id, display, source, msg_id, age_secs, "fresh" if fresh else "retro"
            )
        except Exception as e:
            logging.error(f"[Disboard] 🙅 Failed to award orb: {e}", exc_info=True)

    @tasks.loop(seconds=30.0)
    async def monitor_loop(self):
        try:
            channel = self.bot.get_channel(BUMP_US_CHANNEL_ID)
            if not isinstance(channel, discord.TextChannel):
                logging.warning("[Disboard] 🙅 BUMP_US_CHANNEL_ID not found or not a TextChannel: id=%s", BUMP_US_CHANNEL_ID)
                return

            logging.debug(
                "[Disboard] 🔄 Polling channel: id=%s name=%s guild=%s",
                channel.id, channel.name, getattr(channel.guild, "name", "unknown")
            )

            bump_message = await find_latest_bump_message(channel)
            if not bump_message:
                logging.info("[Disboard] 🙅 No recent bump found.")
                return

            created_at = bump_message.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            now = datetime.now(tz=timezone.utc)
            time_since_bump = (now - created_at)
            age_secs = int(time_since_bump.total_seconds())
            remaining = REMINDER_COOLDOWN - time_since_bump
            remind_at = created_at + REMINDER_COOLDOWN
            remind_threshold = remind_at - timedelta(seconds=5)

            logging.info(
                "[Disboard] ⏱️ Bump timing: message_id=%s created_at=%s now=%s "
                "age_secs=%d remind_at=%s threshold=%s remaining_to_remind_secs=%d",
                getattr(bump_message, "id", "unknown"),
                created_at.isoformat(),
                now.isoformat(),
                age_secs,
                remind_at.isoformat(),
                remind_threshold.isoformat(),
                int(max(0, remaining.total_seconds())),
            )

            # 1) Award (fresh or retro)
            await self._maybe_award(bump_message=bump_message, age_secs=age_secs)

            # 2) Reminder timing & dispatch
            should_remind = (
                (self._last_reminded_bump_id != bump_message.id)
                and (now >= remind_threshold)
            )
            logging.debug(
                "[Disboard] 🔔 Reminder check: should_remind=%s last_reminded=%s msg_id=%s now>=threshold=%s",
                should_remind, self._last_reminded_bump_id, bump_message.id, now >= remind_threshold
            )
            if not should_remind:
                return

            ping_roles = load_json(PING_FILE_PATH, {})
            ping_ids = ping_roles.get("BUMP_PING_1", [])
            generic = build_generic_reminder(channel.guild.name)

            logging.info(
                "[Disboard] 📡 Reminder dispatch prep: subscribers=%d file=%s",
                len(ping_ids), PING_FILE_PATH
            )

            if not ping_ids:
                await send_as_webhook(channel, "disboard", content=generic)
                self._last_reminded_bump_id = bump_message.id
                logging.info("[Disboard] 📣 Sent reminder without mentions (no subscribers). msg_id=%s", bump_message.id)
                return

            ping_toggles = load_ping_toggles()
            eligible_ping_ids, debug_rows = select_eligible_users(
                guild=channel.guild,
                candidate_ids=ping_ids,
                ping_toggles=ping_toggles,
            )
            logging.info(
                "[Disboard] ✅ Eligibility: total_subscribers=%d eligible=%d sample=%s",
                len(ping_ids), len(eligible_ping_ids),
                debug_rows[:5] + (['...'] if len(debug_rows) > 5 else [])
            )

            if not eligible_ping_ids:
                await send_as_webhook(channel, "disboard", content=generic)
                self._last_reminded_bump_id = bump_message.id
                logging.info("[Disboard] 📣 Sent reminder without mentions (no eligible users). msg_id=%s", bump_message.id)
                return

            shuffled_ids, mentions = shuffled_mentions(eligible_ping_ids)
            await send_as_webhook(channel, "disboard", content=generic + "\n" + mentions)
            self._last_reminded_bump_id = bump_message.id
            logging.info(
                "[Disboard] 📣 Reminder sent with mentions: pinged=%d first5=%s msg_id=%s",
                len(shuffled_ids), shuffled_ids[:5], bump_message.id
            )

        except Exception as e:
            logging.error(f"[Disboard] ❗ Error in bump monitor loop: {e}", exc_info=True)

    @monitor_loop.before_loop
    async def before_monitor_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(DisboardCog(bot))
