# pycord/events/event_fetch.py

import aiohttp
import discord
import asyncio
from configs.config_logging import logging
from configs.config_general import BOT_TOKEN, BOT_GUILD_ID

__all__ = [
    "fetch_full_event",
    "log_event_attributes",
]

async def fetch_full_event(event: discord.ScheduledEvent) -> discord.ScheduledEvent:
    """
    Attempt to re-fetch the full scheduled event object from the guild to ensure
    we have complete data. Falls back to the passed event on failure.
    """
    try:
        full = await event.guild.fetch_scheduled_event(event.id)
        logging.info("[EventCreate] Fetched full event")
        logging.info(f"[EventCreate] Full event object: {full!r}")
        return full
    except Exception:
        logging.exception("[EventCreate] Fetch failed; using partial event")
        return event

async def log_event_attributes(event: discord.ScheduledEvent):
    """
    Log key event attributes. Handles 'location' and image URL specially.
    """
    attrs = (
        "id", "name", "description", "creator_id", "status",
        "start_time", "end_time", "privacy_level"
    )

    for attr in attrs:
        try:
            value = getattr(event, attr, None)
            if value is not None:
                logging.info(f"[EventCreate] {attr}: {value}")
        except Exception:
            logging.warning(f"[EventCreate] Could not read attr '{attr}'")

    # Fetch image hash via raw API and construct image URL
    await fetch_and_log_event_image(event.id)

    # Handle 'location' specially
    try:
        loc = getattr(event, "location", None)
        if loc:
            loc_type = getattr(loc, "type", None)
            loc_value = getattr(loc, "value", None)

            if loc_type and loc_value:
                if loc_type.name == "voice" and hasattr(loc_value, "mention"):
                    logging.info(f"[EventCreate] location (voice): {loc_value.mention} (id={loc_value.id})")
                elif loc_type.name == "external":
                    logging.info(f"[EventCreate] location (external): {loc_value}")
                else:
                    logging.info(f"[EventCreate] location (type={loc_type.name}): {loc_value}")
            else:
                logging.info(f"[EventCreate] location (raw): {loc}")
        else:
            logging.info("[EventCreate] location: None")
    except Exception:
        logging.exception("[EventCreate] Failed to log location details")

async def fetch_and_log_event_image(event_id: int) -> str | None:
    url = f"https://discord.com/api/v10/guilds/{BOT_GUILD_ID}/scheduled-events/{event_id}"
    headers = {
        "Authorization": f"Bot {BOT_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            for attempt in range(5):  # Retry up to 3 times
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        image_hash = data.get("image")
                        if image_hash:
                            image_url = f"https://cdn.discordapp.com/guild-events/{event_id}/{image_hash}.png?size=4096"
                            logging.info(f"[EventCreate] image URL: {image_url}")
                            return image_url
                        else:
                            logging.info("[EventCreate] image: None")
                            return None
                    elif resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 2))
                        logging.warning(f"[EventCreate] Hit rate limit (HTTP 429). Retrying in {retry_after} seconds...")
                        await asyncio.sleep(retry_after)
                    else:
                        logging.warning(f"[EventCreate] Failed to fetch image (HTTP {resp.status})")
                        return None
    except Exception:
        logging.exception("[EventCreate] Exception during fetch_and_log_event_image")

    return None