# cogs/reactions/utils.py
from __future__ import annotations
from typing import Iterable, Optional
import discord

from configs.config_logging import logging
from configs.config_general import BOT_GUILD_ID

def is_text_channel(channel: Optional[discord.abc.GuildChannel]) -> bool:
    return isinstance(channel, discord.TextChannel)

def should_skip_channel(channel: Optional[discord.abc.GuildChannel]) -> bool:
    return not is_text_channel(channel) or (
        hasattr(channel, "guild") and channel.guild and channel.guild.id != BOT_GUILD_ID
    )

def normalize_emoji(emoji: discord.PartialEmoji | str) -> str:
    return emoji.name if isinstance(emoji, discord.PartialEmoji) else str(emoji)

async def fetch_message_or_none(
    channel: discord.TextChannel, message_id: int
) -> Optional[discord.Message]:
    try:
        return await channel.fetch_message(message_id)
    except Exception as e:
        logging.warning(f"[FetchMessage] Failed to fetch message {message_id}: {e}")
        return None

async def count_user_reacts_on_message(message: discord.Message, user_id: int) -> int:
    count = 0
    for react in message.reactions:
        try:
            async for u in react.users():
                if u.id == user_id:
                    count += 1
                    break
        except Exception:
            continue
    return count

# Optional scheduler wrapper; uses discord loop
def schedule_tasks(bot: discord.Client, tasks: Iterable["discord.abc.Coroutine"] | Iterable["discord.Task"]) -> None:
    for t in tasks:
        try:
            bot.loop.create_task(t)  # type: ignore[attr-defined]
        except Exception as e:
            logging.warning(f"[Scheduler] Failed to schedule task: {e}")

# --- Reaction bookkeeping shared util ---
from configs.config_files import (
    REACTIONS_GIVEN_FILE,
    REACTIONS_RECEIVED_FILE,
    REACTIONS_DETAIL_FILE,
)
from utils.utils import increment_json_count, increment_reaction_detail

async def track_reaction_counts_and_details(
    message: discord.Message, reactor_user_id: int, emoji_str: str
) -> None:
    msg_author = message.author
    increment_json_count(REACTIONS_RECEIVED_FILE, msg_author.id)
    increment_json_count(REACTIONS_GIVEN_FILE, reactor_user_id)

    increment_reaction_detail(REACTIONS_DETAIL_FILE, msg_author.id, "received", emoji_str)
    increment_reaction_detail(REACTIONS_DETAIL_FILE, reactor_user_id, "given", emoji_str)

    # Feed into close-circle stats (guarded; local import to avoid cycles)
    try:
        from cogs.stats.close_circle.update import update_reactions_proximity
        react_obj = next((r for r in message.reactions if str(r.emoji) == emoji_str), None)
        member = message.guild.get_member(reactor_user_id) if message.guild else None
        if member and react_obj and not member.bot:
            update_reactions_proximity(react_obj, member)
    except Exception as e:
        logging.debug(f"[CloseCircle] Skipped update_reactions_proximity: {e}")
