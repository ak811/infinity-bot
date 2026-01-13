# pycord/events/register_events.py

import re
import discord
from discord.ext import commands
from pycord.bot import bot_pycord
from configs.config_general import BOT_GUILD_ID
from configs.config_logging import logging

from .event_fetch import fetch_full_event, log_event_attributes, fetch_and_log_event_image
from .event_host_location import (
    resolve_event_host,
    resolve_event_location,
    extract_voice_channel,
    resolve_event_channel_obj,
)
from .event_update_handler import handle_scheduled_event_update
from .event_logging import log_event_message
from .donation_view import send_donation_message
from .event_ping import event_voice_channel_map, attendance_start, attendees
from configs.helper import send_as_webhook
from datetime import datetime

CHANNEL_URL_RE = re.compile(r"discord\.com/channels/(\d+)/(\d+)")

# ------------------------
# Command helpers
# ------------------------

async def _fetch_event_or_reply(ctx: commands.Context, event_id: int) -> discord.ScheduledEvent | None:
    """Fetch a scheduled event by id; reply with a friendly error if not found."""
    try:
        evt = await ctx.guild.fetch_scheduled_event(event_id)  # type: ignore
    except Exception:
        content = f"❌ I couldn’t find an event with ID `{event_id}` in this server."
        await send_as_webhook(ctx, "event", content=content)
        return None
    return evt

def _is_vc_or_stage(ch: discord.abc.GuildChannel | None) -> bool:
    return isinstance(ch, (discord.VoiceChannel, discord.StageChannel))

def _channel_matches_event_vc(invocation_ch: discord.abc.GuildChannel, event_vc: discord.abc.GuildChannel) -> bool:
    """
    Returns True if the command's channel is the same as the event's VC/Stage,
    or if the command was run in a thread whose parent is that VC/Stage (voice text chat).
    """
    if invocation_ch.id == event_vc.id:
        return True
    parent = getattr(invocation_ch, "parent", None)
    if parent and getattr(parent, "id", None) == event_vc.id:
        return True
    return False

async def _ensure_host_active(ctx: commands.Context, evt: discord.ScheduledEvent) -> bool:
    """Ensure the invoker is the host (creator_id) and the event is active."""
    if evt.status != EventStatus.active:
        content = "⏳ That event isn’t active right now."
        await send_as_webhook(ctx, "event", content=content)
        return False
    if evt.creator_id != ctx.author.id:
        content = "🙅 Only the **host** of this event can use this command."
        await send_as_webhook(ctx, "event", content=content)
        return False
    return True

async def _resolve_event_vc_or_reply(ctx: commands.Context, evt: discord.ScheduledEvent) -> discord.abc.GuildChannel | None:
    """Resolve the event’s actual VC/Stage channel; reply if it isn’t one."""
    ch = resolve_event_channel_obj(evt)
    if not _is_vc_or_stage(ch):
        content = "📍 I couldn’t resolve a **Voice/Stage** channel for that event."
        await send_as_webhook(ctx, "event", content=content)
        
        return None
    return ch

async def _enforce_same_channel(ctx: commands.Context, vc: discord.abc.GuildChannel) -> bool:
    """Require the command to be used in the same channel as the event’s VC/Stage (or its voice text chat)."""
    if _channel_matches_event_vc(ctx.channel, vc):  # type: ignore
        return True
    content = f"📍 Please run this in the event’s channel: <#{vc.id}>"
    await send_as_webhook(ctx, "event", content=content)
        
    return False

async def _ping_all_subscribers(evt: discord.ScheduledEvent, dest: discord.abc.Messageable):
    """Ping all interested (subscribed) users in batches to avoid message limits."""
    mentions: list[str] = []
    async for user in evt.subscribers(limit=None):
        mentions.append(user.mention)

    if not mentions:
        await send_as_webhook(dest, "event", content="🔔 No subscribers to ping for this event.")
        return

    header = f"## 📣 **{evt.name}** — host ping\n"
    BATCH = 20  # conservative for length limits
    for i in range(0, len(mentions), BATCH):
        chunk = " ".join(mentions[i:i+BATCH])
        content = (header if i == 0 else "") + chunk
        await send_as_webhook(dest, "event", content=content)

def _build_queue_embed(evt: discord.ScheduledEvent, vc: discord.abc.GuildChannel) -> discord.Embed:
    """
    Build an embed showing current 'queue' (members in VC/Stage) ordered by join time
    using attendance_start[(event_id, user_id)] when available.
    """
    # Collect members from the channel
    members = []
    try:
        members = list(getattr(vc, "members", []))
    except Exception:
        members = []

    # Pair with join times (may be None if not tracked)
    records = []
    for m in members:
        jt = attendance_start.get((evt.id, m.id))  # datetime or None
        records.append((m, jt))

    # Sort: known join times first (oldest → newest), then unknown by display name
    def sort_key(item):
        m, jt = item
        return (0, jt) if jt else (1, m.display_name.casefold())
    records.sort(key=sort_key)

    embed = discord.Embed(
        title=f"🎟️ Event Queue — {evt.name}",
        description=f"Channel: <#{vc.id}>",
        color=discord.Color.blurple()
    )

    if not records:
        embed.add_field(name="Queue", value="Nobody is currently connected.", inline=False)
        return embed

    lines = []
    for idx, (m, jt) in enumerate(records, start=1):
        if jt:
            ts = int(jt.timestamp())
            lines.append(f"**{idx}.** {m.mention} — joined <t:{ts}:R>")
        else:
            lines.append(f"**{idx}.** {m.mention} — joined time unknown")

    embed.add_field(name=f"Queue ({len(records)} online)", value="\n".join(lines), inline=False)
    return embed

# ------------------------
# High-level Event Hooks
# ------------------------

@bot_pycord.event
async def on_ready():
    logging.info(f"[PycordBot] ✅ Logged in as {bot_pycord.user} (ID: {bot_pycord.user.id})")


@bot_pycord.event
async def on_message(message: discord.Message):
    """Forward command messages to command processor (guild + prefix check)."""
    if (
        message.guild
        and message.guild.id == BOT_GUILD_ID
        and not message.author.bot
        and message.content.startswith("!")
    ):
        await bot_pycord.process_commands(message)

@bot_pycord.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    """
    Track VC attendance for events. If a user stays ≥10 minutes,
    add them to the event's attendee set.
    """
    try:
        for event_id, vc_id in event_voice_channel_map.items():
            # user just joined the event VC
            if after.channel and after.channel.id == vc_id and (before.channel is None or before.channel.id != vc_id):
                attendance_start[(event_id, member.id)] = datetime.now()

            # user just left the event VC
            if before.channel and before.channel.id == vc_id and (after.channel is None or after.channel.id != vc_id):
                key = (event_id, member.id)
                start = attendance_start.pop(key, None)
                if start and (datetime.now() - start).total_seconds() >= 600:  # 10 min
                    attendees.setdefault(event_id, set()).add(member.id)

    except Exception:
        logging.exception("[Attendance] Error tracking VC attendance")

@bot_pycord.event
async def on_scheduled_event_create(event: discord.ScheduledEvent):
    """Creation: fetch full event, log details, post summary."""
    logging.info(f"[EventCreate] Event created: {event.name} (ID: {event.id})")

    full_event = await fetch_full_event(event)
    await log_event_attributes(full_event)

    host = await resolve_event_host(full_event)
    location = await resolve_event_location(full_event)
    start_ts = get_start_timestamp(full_event)

    logging.info(f"[EventCreate] Final host: {host}")
    logging.info(f"[EventCreate] Final location: {location}")

    # Fetch image URL
    image_url = await fetch_and_log_event_image(full_event.id)
    event_url = f"https://discord.com/events/{full_event.guild.id}/{full_event.id}"
    
    # Build embed
    embed = discord.Embed(
        title=f"📅 New Event: {full_event.name}",
        description=(
                f"👤 **Host:** {host}\n"
                f"⏰ **Starts:** <t:{start_ts}:F>\n"
                f"📍 **Location:** {location}\n"
                f"🔗 **Event Link:** [Click to view]({event_url})"
            ),
            color=discord.Color.blue()
    )

    if image_url:
        embed.set_image(url=image_url)

    await log_event_message(full_event.guild, embed=embed)

@bot_pycord.event
async def on_scheduled_event_delete(event: discord.ScheduledEvent):
    logging.info(f"[EventDelete] Event deleted: {event.name}")
    await log_event_message(event.guild, f"🗑️ **Event Canceled:** {event.name}")

@bot_pycord.event
async def on_scheduled_event_update(before: discord.ScheduledEvent, after: discord.ScheduledEvent):
    logging.info(f"[EventUpdate] {before.name} → {after.status.name}")
    await handle_scheduled_event_update(before, after)

# ------------------------
# Command Group: !event
# ------------------------

@bot_pycord.group(name="event", invoke_without_command=True)
async def event_group(ctx: commands.Context):
    """
    !event — Show the list of event commands.
    This can be used anywhere in the server.
    """
    embed = discord.Embed(
        title="📖 Event Commands",
        color=discord.Color.green(),
        description=(
            "**!event ping `<event_id>`**\n"
            "• Host-only. Use in the **same VC/Stage channel** as the event.\n"
            "• Pings all interested (subscribed) members for the event.\n\n"
            "**!event donation `<event_id>`**\n"
            "• Host-only. Use in the **same VC/Stage channel** as the event.\n"
            "• Posts the donation buttons (🪙🔮⭐💎) for attendees to tip the host.\n\n"
            "**!q**\n"
            "• Use in the **same VC/Stage channel** as the event.\n"
            "• Shows the current queue."
        )
    )
    await send_as_webhook(ctx, "event", embed=embed)

@event_group.command(name="ping")
async def event_ping(ctx: commands.Context, event_id: int):
    """!event ping <event_id> — Host-only. Must be run in the same channel as the event’s VC/Stage. Pings all subscribers."""
    if not ctx.guild:
        return
    evt = await _fetch_event_or_reply(ctx, event_id)
    if not evt:
        return
    if not await _ensure_host_active(ctx, evt):
        return
    vc = await _resolve_event_vc_or_reply(ctx, evt)
    if not vc:
        return
    if not await _enforce_same_channel(ctx, vc):
        return
    await _ping_all_subscribers(evt, vc)
    logging.info(f"[Cmd:event ping] Host {ctx.author.id} pinged subscribers for {evt.id} in {vc.id}")
    try:
        await ctx.message.add_reaction("✅")
    except Exception:
        pass

@event_group.command(name="donation")
async def event_donation(ctx: commands.Context, event_id: int):
    """!event donation <event_id> — Host-only. Must be run in the same channel as the event’s VC/Stage. Shows the donation view."""
    if not ctx.guild:
        return
    evt = await _fetch_event_or_reply(ctx, event_id)
    if not evt:
        return
    if not await _ensure_host_active(ctx, evt):
        return
    vc = await _resolve_event_vc_or_reply(ctx, evt)
    if not vc:
        return
    if not await _enforce_same_channel(ctx, vc):
        return
    await send_donation_message(vc, evt.creator_id, evt.name)
    logging.info(f"[Cmd:event donation] Host {ctx.author.id} posted donation view for {evt.id} in {vc.id}")
    try:
        await ctx.message.add_reaction("💝")
    except Exception:
        pass

# ------------------------
# Local Helpers
# ------------------------

def get_start_timestamp(event: discord.ScheduledEvent):
    """Return int UNIX timestamp or 'Unknown'."""
    try:
        if getattr(event, "start_time", None):
            return int(event.start_time.timestamp())
    except Exception:
        logging.exception("[EventCreate] start_time to ts failed")
    return "Unknown"
