# pycord/events/event_ping.py

import asyncio
import discord
from discord import VoiceChannel, StageChannel
from datetime import datetime
from enum import IntEnum

from configs.config_logging import logging
from configs.helper import send_as_webhook
from .donation_view import send_donation_message


scheduled_donation_tasks: dict[int, asyncio.Task] = {}


def _status_val(s) -> int:
    """Normalize status to an int across discord libs (Enum/IntEnum/int)."""
    try:
        return int(getattr(s, "value", s))
    except Exception:
        return int(s)  # last resort


# If the library has a real ScheduledEventStatus, use it.
# Otherwise, fall back to Discord API status integer values.
EventStatus = getattr(discord, "ScheduledEventStatus", None)
if EventStatus is None:
    class EventStatus(IntEnum):
        scheduled = 1
        active = 2
        completed = 3
        canceled = 4


# maps event_id → VC/Stage channel id
event_voice_channel_map: dict[int, int] = {}
# track when a user joined: (event_id, user_id) → datetime
attendance_start: dict[tuple[int, int], datetime] = {}
# final attendees (≥10 min): event_id → set of user_ids
attendees: dict[int, set[int]] = {}


async def ping_interested_users(event: discord.ScheduledEvent, channel: discord.abc.Messageable):
    """
    Ping up to 20 subscribers when the event becomes active.
    Then, if this is a voice/stage channel, schedule periodic donation reminders.
    """
    try:
        mentions: list[str] = []
        async for user in event.subscribers(limit=None):
            mentions.append(user.mention)
            if len(mentions) >= 20:
                break

        if mentions:
            content = f"## 📣 **{event.name}** is starting right now! 🥳🎉\n\n" + " ".join(mentions)
            await send_as_webhook(channel, "event", content=content)
            logging.info(f"[EventPing] Pinged {len(mentions)} users.")
        else:
            logging.info("[EventPing] No subscribers to ping.")

        # schedule reminders only in VC/Stage
        if isinstance(channel, (VoiceChannel, StageChannel)) and event.id not in scheduled_donation_tasks:
            task = asyncio.create_task(
                repeat_donation_reminder(event.creator_id, event.name, channel, event.id)
            )
            scheduled_donation_tasks[event.id] = task

            event_voice_channel_map[event.id] = channel.id
            attendees[event.id] = set()

            logging.info(f"[EventReminder] Started reminder task for {event.name}")

    except Exception:
        logging.exception("[EventPing] Failed to ping or schedule reminders.")


async def repeat_donation_reminder(
    host_id: int,
    event_name: str,
    channel: discord.abc.Messageable,
    event_id: int
):
    """Every 30 minutes while the event is still active, resend the donation prompt."""
    try:
        while True:
            await asyncio.sleep(1800)  # 30 minutes

            guild = getattr(channel, "guild", None)
            if guild is None:
                break

            evt = await guild.fetch_scheduled_event(event_id)
            if _status_val(evt.status) != _status_val(EventStatus.active):
                break

            await send_donation_message(channel, host_id, event_name)

    except asyncio.CancelledError:
        logging.info(f"[EventReminder] Cancelled reminder for {event_name}")
    except Exception:
        logging.exception(f"[EventReminder] Error in reminder loop for {event_name}")
    finally:
        scheduled_donation_tasks.pop(event_id, None)
