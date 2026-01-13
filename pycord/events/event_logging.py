# pycord/events/event_logging.py

import discord
from configs.config_channels import EVENTS_CHANNEL_ID
from configs.config_logging import logging
from configs.helper import send_as_webhook

__all__ = [
    "log_event_message",
]

async def log_event_message(
    guild: discord.Guild,
    title: str = None,
    body: str = "",
    *,
    embed: discord.Embed = None,
    channel_id: int = EVENTS_CHANNEL_ID
):
    """
    Send an embed to the logs channel (or provided channel_id) using the 'event' pet persona.
    Supports either passing title+body or a custom embed directly.
    """
    try:
        ch = guild.get_channel(channel_id)
        if not ch:
            logging.warning("[EventLog] Log channel not found.")
            return

        if embed is None:
            embed = discord.Embed(
                title=title or "📅 Event Log",
                description=body or "",
                color=discord.Color.blurple()
            )

        await send_as_webhook(ch, "event", embed=embed)
        logging.info(f"[EventLog] {title or '[Embed sent]'} | {body}")
    except Exception:
        logging.exception("[EventLog] Failed to send event log.")
