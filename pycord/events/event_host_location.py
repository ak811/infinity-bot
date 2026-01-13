# pycord/events/event_host_location.py

import re
import discord
from pycord.bot import get_bot
from configs.config_logging import logging
bot = get_bot()

__all__ = [
    "resolve_event_host",
    "resolve_event_location",          # legacy display API
    "resolve_event_location_display",  # new explicit name
    "resolve_event_channel_obj",       # new channel object resolver
    "extract_voice_channel",
]

# Patterns
CHANNEL_URL_RE      = re.compile(r"discord\.com/channels/(\d+)/(\d+)")
CHANNEL_MENTION_RE  = re.compile(r"<#(\d+)>")


# ---------------------------
# Host Resolution
# ---------------------------

async def resolve_event_host(event: discord.ScheduledEvent) -> str:
    """
    Host resolution priority:
      1. creator_id -> guild member
      2. creator_id -> fetch user
      3. event.creator object
      4. fallback id / 'Unknown'
    """
    guild = event.guild
    cid = getattr(event, "creator_id", None)
    if cid:
        member = guild.get_member(cid)
        if member:
            logging.info(f"[EventHost] Host guild member: {member.display_name}")
            return member.display_name
        try:
            user = await bot.fetch_user(cid)
            logging.info(f"[EventHost] Host fetched user: {user.display_name}")
            return user.display_name
        except Exception:
            logging.warning(f"[EventHost] Fetch user failed for {cid}")
            return f"User ID: {cid}"

    creator = getattr(event, "creator", None)
    if creator:
        logging.info(f"[EventHost] Host from creator object: {creator.display_name}")
        return creator.display_name
    return "Unknown"


# ---------------------------
# Location (Display + Channel)
# ---------------------------

def resolve_event_channel_obj(event: discord.ScheduledEvent) -> discord.abc.GuildChannel | None:
    """
    Attempt to resolve the *channel object* where an event is happening, even if event.channel is None.

    Order:
      1. event.channel if already a channel instance.
      2. Parse event.location (if present):
         a. Channel URL
         b. Channel mention <#id>
         c. Exact channel name (case-insensitive)
    Returns: channel object or None.
    """
    guild = event.guild
    if not guild:
        return None

    # 1. Direct channel attribute
    ch = getattr(event, "channel", None)
    if isinstance(ch, (discord.VoiceChannel, discord.StageChannel, discord.TextChannel, discord.ForumChannel, discord.CategoryChannel)):
        return ch

    loc = getattr(event, "location", None)
    if not loc:
        return None

    loc_str = str(loc).strip()

    # 2a. Channel URL
    m = CHANNEL_URL_RE.search(loc_str)
    if m:
        channel_id = int(m.group(2))
        ch_obj = guild.get_channel(channel_id)
        if ch_obj:
            logging.info(f"[EventLoc] Resolved channel from URL: {ch_obj} (id={channel_id})")
            return ch_obj

    # 2b. Channel mention
    m2 = CHANNEL_MENTION_RE.search(loc_str)
    if m2:
        channel_id = int(m2.group(1))
        ch_obj = guild.get_channel(channel_id)
        if ch_obj:
            logging.info(f"[EventLoc] Resolved channel from mention: {ch_obj} (id={channel_id})")
            return ch_obj

    # 2c. Channel name (exact, case-insensitive)
    lowered = loc_str.casefold()
    for ch_obj in guild.channels:
        name = getattr(ch_obj, "name", None)
        if name and name.casefold() == lowered:
            logging.info(f"[EventLoc] Resolved channel from name: {ch_obj} (id={ch_obj.id})")
            return ch_obj

    return None


async def resolve_event_location_display(event: discord.ScheduledEvent) -> str:
    """
    User-facing location string (channel mention if possible).
    Priority:
      1. event.location parsed (URL -> mention, mention stays, name -> mention)
      2. event.channel mention
      3. fallback text or 'No location'
    """
    guild = event.guild
    if not guild:
        return "No location"

    # Try event.location first
    loc = getattr(event, "location", None)
    if loc:
        loc_str = str(loc).strip()

        # URL -> channel mention
        m = CHANNEL_URL_RE.search(loc_str)
        if m:
            chan_id = int(m.group(2))
            return f"<#{chan_id}>"

        # Already a mention
        if CHANNEL_MENTION_RE.search(loc_str):
            return loc_str

        # Invite link -> server label
        if "discord.gg/" in loc_str or "discord.com/invite/" in loc_str:
            return f"🌐 {guild.name} Server"

        # Exact channel name
        lowered = loc_str.casefold()
        for ch in guild.channels:
            name = getattr(ch, "name", None)
            if name and name.casefold() == lowered:
                return f"<#{ch.id}>"

        # Fallback literal text
        return loc_str

    # Fallback: event.channel attribute
    ch = getattr(event, "channel", None)
    if isinstance(ch, (discord.VoiceChannel, discord.StageChannel, discord.TextChannel, discord.ForumChannel)):
        return f"<#{ch.id}>"

    return "No location"


# Backwards-compatible name (returns display string)
async def resolve_event_location(event: discord.ScheduledEvent) -> str:  # noqa: D401
    return await resolve_event_location_display(event)


def extract_voice_channel(event: discord.ScheduledEvent):
    """
    Return voice/stage channel if present (legacy helper).
    Prefer resolve_event_channel_obj for broader channel types.
    """
    try:
        ch = getattr(event, "channel", None)
        if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
            return ch
    except Exception:
        logging.exception("[EventLoc] Voice channel extraction failed")
    return None
