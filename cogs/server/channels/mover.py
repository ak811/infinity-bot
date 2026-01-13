# cogs/server/channels/mover.py
from __future__ import annotations
import asyncio
import discord
from . import activity, positions
from .archive_config import (
    ARCHIVE_CATEGORY_ID, ARCHIVE_CATEGORY_NAME,
    PINNED_CHANNEL_IDS, ARCHIVE_TEXT, ARCHIVE_VOICE, REQUIRE_PUBLIC,
    EXCLUDED_CATEGORY_IDS, EXCLUDED_CHANNEL_IDS
)
from configs.config_channels import JOIN_TO_CREATE_CHANNEL_ID


def _is_public(ch: discord.abc.GuildChannel) -> bool:
    try:
        return ch.permissions_for(ch.guild.default_role).view_channel
    except Exception:
        return False


async def get_archive_category(guild: discord.Guild):
    if ARCHIVE_CATEGORY_ID:
        cat = guild.get_channel(ARCHIVE_CATEGORY_ID)
        if isinstance(cat, discord.CategoryChannel):
            return cat
    for cat in guild.categories:
        if cat.name == ARCHIVE_CATEGORY_NAME:
            return cat
    return None


def is_in_archive(channel, archive_category) -> bool:
    return channel.category and archive_category and channel.category.id == archive_category.id


def _is_excluded(channel: discord.abc.GuildChannel) -> bool:
    if channel.id in EXCLUDED_CHANNEL_IDS:
        return True
    if channel.category and channel.category.id in EXCLUDED_CATEGORY_IDS:
        return True
    return False


async def archive_if_inactive(guild: discord.Guild, channel: discord.abc.GuildChannel) -> bool:
    # hard excludes first
    if _is_excluded(channel):
        return False

    if channel.id in PINNED_CHANNEL_IDS:
        return False
    if REQUIRE_PUBLIC and not _is_public(channel):
        return False
    if isinstance(channel, discord.TextChannel) and not ARCHIVE_TEXT:
        return False
    if isinstance(channel, discord.VoiceChannel) and not ARCHIVE_VOICE:
        return False

    archive_cat = await get_archive_category(guild)
    if not archive_cat or is_in_archive(channel, archive_cat):
        return False
    if await activity.is_channel_active(channel):
        return False

    await positions.move_to_archive(channel, archive_cat)
    return True


# --- NEW: helper to move/sync a VC under Join-to-Create ---
async def _move_vc_under_join_to_create(guild: discord.Guild, vc: discord.VoiceChannel) -> None:
    jtc = guild.get_channel(int(JOIN_TO_CREATE_CHANNEL_ID))
    if not isinstance(jtc, (discord.VoiceChannel, discord.StageChannel)):
        return
    join_cat = jtc.category
    if not join_cat:
        return
    try:
        # Step 1: move to JTC category and sync perms
        if vc.category is None or vc.category.id != join_cat.id:
            await vc.edit(category=join_cat, sync_permissions=True)
            await asyncio.sleep(0.2)  # allow category move to apply
        else:
            # already there — ensure perms are synced anyway
            try:
                await vc.edit(sync_permissions=True)
            except Exception:
                pass

        # Step 2: position just below JTC
        await vc.edit(position=jtc.position + 1)
    except Exception:
        pass


async def unarchive_on_message(message: discord.Message) -> None:
    ch = message.channel
    # Accept TextChannel and VoiceChannel (voice text chat)
    if not isinstance(ch, (discord.TextChannel, discord.VoiceChannel)):
        return

    archive_cat = await get_archive_category(ch.guild)
    if not archive_cat or not is_in_archive(ch, archive_cat):
        return

    # If a message is posted in a VoiceChannel inside Archive:
    # move it under Join-to-Create (sync perms + position).
    if isinstance(ch, discord.VoiceChannel):
        await _move_vc_under_join_to_create(ch.guild, ch)
        return

    # Otherwise (TextChannel), restore to original placement.
    await positions.restore_to_original(ch.guild, ch)
