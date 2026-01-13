# pycord/events/event_update_handler.py

import discord
from configs.config_logging import logging
from configs.config_channels import EVENTS_CHANNEL_ID, LOGS_CHANNEL_ID
from .event_logging import log_event_message
from .donation_view import send_donation_message, donation_logs
from .event_ping import scheduled_donation_tasks, EventStatus, ping_interested_users, attendees
from .event_fetch import fetch_and_log_event_image
from .event_host_location import resolve_event_location_display, resolve_event_channel_obj
from configs.helper import send_as_webhook

__all__ = [
    "handle_scheduled_event_update",
]


def _status_val(s) -> int:
    try:
        return int(getattr(s, "value", s))
    except Exception:
        return int(s)


async def handle_scheduled_event_update(before: discord.ScheduledEvent, after: discord.ScheduledEvent):
    """
    Central update handler for scheduled events:
      - Canceled
      - (Re)Scheduled
      - Started (Active)
      - Completed
    """
    guild = after.guild
    event_name = after.name

    try:
        # --------------------------------------------------
        # CANCELED
        # --------------------------------------------------
        if _status_val(after.status) == _status_val(EventStatus.canceled) and _status_val(before.status) != _status_val(EventStatus.canceled):
            await log_event_message(
                guild,
                f"### 🙅 {event_name} was canceled",
                channel_id=EVENTS_CHANNEL_ID,
            )

        # --------------------------------------------------
        # (RE)SCHEDULED
        # --------------------------------------------------
        elif _status_val(after.status) == _status_val(EventStatus.scheduled) and _status_val(before.status) != _status_val(EventStatus.scheduled):
            start_ts = int(after.start_time.timestamp()) if after.start_time else "Unknown"
            location_display = await resolve_event_location_display(after)
            image_url = await fetch_and_log_event_image(after.id)
            event_url = f"https://discord.com/events/{guild.id}/{after.id}"

            embed = discord.Embed(
                title=f"▶️ Next Event: {event_name}",
                description=(
                    f"**⏰ Starts:** <t:{start_ts}:F>\n"
                    f"**📍 Location:** {location_display}\n"
                    f"**🔗 Event Link:** [Open Event]({event_url})"
                ),
                color=discord.Color.green()
            )
            if image_url:
                embed.set_image(url=image_url)

            await log_event_message(guild, embed=embed, channel_id=EVENTS_CHANNEL_ID)

        # --------------------------------------------------
        # STARTED (ACTIVE)
        # --------------------------------------------------
        elif _status_val(after.status) == _status_val(EventStatus.active) and _status_val(before.status) != _status_val(EventStatus.active):
            start_ts = int(after.start_time.timestamp()) if after.start_time else "Unknown"
            location_display = await resolve_event_location_display(after)
            image_url = await fetch_and_log_event_image(after.id)
            event_url = f"https://discord.com/events/{guild.id}/{after.id}"

            embed = discord.Embed(
                title=f"▶️ Event Started: {event_name}",
                description=(
                    f"**⏰ Started:** <t:{start_ts}:F>\n"
                    f"**📍 Location:** {location_display}\n"
                    f"**🔗 Event Link:** [Open Event]({event_url})"
                ),
                color=discord.Color.green()
            )
            if image_url:
                embed.set_image(url=image_url)

            await log_event_message(guild, embed=embed, channel_id=EVENTS_CHANNEL_ID)

            target_channel = resolve_event_channel_obj(after)
            if target_channel is None:
                logging.warning(f"[EventStart] Could not resolve channel object from event; fallback EVENTS_CHANNEL_ID ({event_name})")
                target_channel = guild.get_channel(EVENTS_CHANNEL_ID)

            if target_channel:
                logging.info(
                    "[EventStart] Using target_channel: "
                    f"name={getattr(target_channel, 'name', 'N/A')} "
                    f"id={getattr(target_channel, 'id', 'N/A')} "
                    f"type={target_channel.__class__.__name__}"
                )
                await ping_interested_users(after, target_channel)
            else:
                logging.error(f"[EventStart] No channel available for pings ({event_name})")

        # --------------------------------------------------
        # COMPLETED
        # --------------------------------------------------
        if _status_val(after.status) == _status_val(EventStatus.completed) and _status_val(before.status) != _status_val(EventStatus.completed):
            await log_event_message(
                guild,
                f"✅ {event_name} event is now finished 🎉",
                channel_id=EVENTS_CHANNEL_ID,
            )

            vc_or_stage = None
            ch = getattr(after, "channel", None)
            if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                vc_or_stage = ch

            if vc_or_stage:
                await send_donation_message(vc_or_stage, after.creator_id, event_name)
                logging.info(f"[EventReminder] Sent final donation message in VC/Stage for {event_name}")
            else:
                logging.warning(f"[EventReminder] No VC/Stage channel found for final donation message of {event_name}")

            key = (after.creator_id, event_name)
            logs = donation_logs.pop(key, [])

            totals = {}
            donor_breakdown = {}
            for donor_id, dtyp, amt in logs:
                totals[dtyp] = totals.get(dtyp, 0) + amt
                donor_breakdown.setdefault(donor_id, {}).setdefault(dtyp, 0)
                donor_breakdown[donor_id][dtyp] += amt

            embed = discord.Embed(
                title=f"💖 Donation Summary: {event_name}",
                color=discord.Color.gold()
            )

            parts = []
            if totals.get("coin"):    parts.append(f"{totals['coin']} 🪙")
            if totals.get("orb"):     parts.append(f"{totals['orb']} 🔮")
            if totals.get("diamond"): parts.append(f"{totals['diamond']} 💎")
            if totals.get("star"):    parts.append(f"{totals['star']} ⭐")
            embed.add_field(name="Total Donations", value=", ".join(parts) or "None", inline=False)

            if donor_breakdown:
                lines = []
                for uid, types in donor_breakdown.items():
                    syms = []
                    for dtyp, cnt in types.items():
                        sym = {"coin":"🪙","orb":"🔮","diamond":"💎","star":"⭐"}[dtyp]
                        syms.append(f"{cnt} {sym}")
                    lines.append(f"<@{uid}>: " + ", ".join(syms))
                embed.add_field(name="Donor Breakdown", value="\n".join(lines), inline=False)

            ev_id = after.id
            att = attendees.pop(ev_id, set())
            embed.add_field(
                name="Attendees (≥10 min)",
                value=(", ".join(f"<@{u}>" for u in att) or "None"),
                inline=False
            )

            log_ch = guild.get_channel(LOGS_CHANNEL_ID)
            if log_ch:
                await send_as_webhook(log_ch, "event", embed=embed)
                logging.info(f"[EventLog] Sent donation summary for {event_name}")
            else:
                logging.warning(f"[EventLog] LOGS_CHANNEL_ID not found for {event_name}")

            task = scheduled_donation_tasks.pop(after.id, None)
            if task:
                task.cancel()
                logging.info(f"[EventReminder] Canceled donation reminder for {event_name}")

    except Exception:
        logging.exception("[EventUpdate] Failed to handle update")
