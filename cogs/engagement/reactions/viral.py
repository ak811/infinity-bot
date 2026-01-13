# cogs/reactions/viral.py
from __future__ import annotations
import json
import asyncio
from pathlib import Path
import discord

from configs.config_channels import (
    JUDGE_ZONE_CHANNEL_ID,
    VIRAL_POSTS_CHANNEL_ID,
    HOME_CATEGORY_ID
)
from configs.helper import send_as_webhook

EXCLUDED_CHANNELS = {JUDGE_ZONE_CHANNEL_ID}
EXCLUDED_CATEGORIES = {HOME_CATEGORY_ID}
UNIQUE_USER_THRESHOLD = 10

# Embed limits
MAX_EMBED_DESCRIPTION_LENGTH = 4096
MAX_FIELD_VALUE_LENGTH = 1024
MAX_ATTACHMENT_SIZE_MB = 25

DATA_DIR = Path("database")
DATA_DIR.mkdir(parents=True, exist_ok=True)
FORWARDED_FILE = DATA_DIR / "forwarded_viral_message_ids.json"

_ids_lock = asyncio.Lock()
_handle_lock = asyncio.Lock()

def _load_forwarded_ids() -> set[int]:
    try:
        with FORWARDED_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {int(x) for x in data}
    except FileNotFoundError:
        return set()
    except Exception:
        return set()

def _save_forwarded_ids_sync(ids: set[int]) -> None:
    tmp_path = FORWARDED_FILE.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(sorted(ids), f, separators=(",", ":"))
    tmp_path.replace(FORWARDED_FILE)

async def _save_forwarded_ids(ids: set[int]) -> None:
    async with _ids_lock:
        _save_forwarded_ids_sync(ids)

forwarded_message_ids: set[int] = _load_forwarded_ids()

async def handle_viral_post_check(bot: discord.Client, payload: discord.RawReactionActionEvent) -> None:
    async with _handle_lock:
        if payload.message_id in forwarded_message_ids:
            return

        channel = bot.get_channel(payload.channel_id)
        if not isinstance(channel, discord.TextChannel):
            return

        if channel.id in EXCLUDED_CHANNELS:
            return

        if channel.category and channel.category.id in EXCLUDED_CATEGORIES:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return

        total_reactions = sum(r.count for r in message.reactions)

        unique_users = set()
        for reaction in message.reactions:
            try:
                async for user in reaction.users():
                    if not user.bot:
                        unique_users.add(user.id)
            except Exception:
                continue

        if len(unique_users) < UNIQUE_USER_THRESHOLD:
            return

        viral_channel = bot.get_channel(VIRAL_POSTS_CHANNEL_ID)
        if not viral_channel:
            return

        description = message.content or ""
        if len(description) > MAX_EMBED_DESCRIPTION_LENGTH:
            description = description[:MAX_EMBED_DESCRIPTION_LENGTH - 3] + "..."

        embed = discord.Embed(
            title="🔥 Viral Post Detected!",
            description=description,
            color=discord.Color.orange(),
        )
        embed.add_field(name="👤 Author", value=message.author.mention[:MAX_FIELD_VALUE_LENGTH], inline=True)
        embed.add_field(name="💬 Channel", value=f"<#{channel.id}>", inline=True)
        embed.add_field(name="⭐ Total Reactions", value=str(total_reactions), inline=True)
        embed.add_field(name="🔗 Jump Link", value=f"[Click to view message]({message.jump_url})", inline=False)

        image_set = False
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image/"):
                embed.set_image(url=attachment.url)
                image_set = True
                break

        files = []
        if not image_set:
            try:
                for a in message.attachments:
                    if a.size <= MAX_ATTACHMENT_SIZE_MB * 1024 * 1024:
                        files.append(await a.to_file())
            except Exception:
                files = []

        try:
            await send_as_webhook(viral_channel, "viral_post", embed=embed, files=files)
            forwarded_message_ids.add(payload.message_id)
            await _save_forwarded_ids(forwarded_message_ids)
        except Exception:
            # swallow to avoid breaking the reaction flow
            return
