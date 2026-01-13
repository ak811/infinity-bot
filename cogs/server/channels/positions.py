# cogs/server/channels/positions.py
from __future__ import annotations
import asyncio
import discord
from ._storage import load_positions, save_positions

_positions_cache: dict[str, dict] | None = None  # keys are str(channel_id)

async def _get_cache() -> dict[str, dict]:
    global _positions_cache
    if _positions_cache is None:
        # normalize keys to str for safety
        raw = await load_positions()
        _positions_cache = {str(k): v for k, v in raw.items()}
    return _positions_cache

async def _save_cache():
    if _positions_cache is not None:
        await save_positions(_positions_cache)

def _ctype(ch) -> str:
    return (
        "text" if isinstance(ch, discord.TextChannel)
        else "voice" if isinstance(ch, discord.VoiceChannel)
        else "other"
    )

def _same_type_siblings(cat: discord.CategoryChannel | None, ch_type: str, exclude_id: int | None = None):
    if not cat:
        return []
    if ch_type == "text":
        siblings = list(cat.text_channels)
    elif ch_type == "voice":
        siblings = list(cat.voice_channels)
    else:
        siblings = list(cat.channels)
    if exclude_id is not None:
        siblings = [c for c in siblings if c.id != exclude_id]
    # Discord already keeps .position, but we sort anyway for determinism
    siblings.sort(key=lambda c: c.position)
    return siblings

async def remember_original_place(channel: discord.abc.GuildChannel) -> None:
    """
    Persist original parent/category, index position, type, and the *next* sibling's id (after_id)
    so we can restore precisely even if other channels moved in the meantime.
    """
    cache = await _get_cache()
    key = str(channel.id)
    if key in cache:
        return

    ch_type = _ctype(channel)
    parent_id = channel.category.id if channel.category else None
    pos = channel.position

    # find next sibling (within same type) in the current category
    after_id = None
    if channel.category:
        siblings = _same_type_siblings(channel.category, ch_type, exclude_id=None)
        try:
            idx = next(i for i, c in enumerate(siblings) if c.id == channel.id)
            if idx + 1 < len(siblings):
                after_id = siblings[idx + 1].id
        except StopIteration:
            pass

    cache[key] = {
        "parent_id": parent_id,
        "position": pos,
        "type": ch_type,
        # optional helper for more exact restore
        "after_id": after_id,
    }
    await _save_cache()

async def original_place(channel_id: int):
    cache = await _get_cache()
    return cache.get(str(channel_id))

# cogs/server/channels/positions.py
async def move_to_archive(channel: discord.abc.GuildChannel, archive_category: discord.CategoryChannel) -> None:
    # persist original place BEFORE moving
    await remember_original_place(channel)
    try:
        await channel.edit(
            category=archive_category,
            position=len(archive_category.channels),
            sync_permissions=True,   # <- inherit archive category perms
        )
    except Exception:
        pass

async def _restore_position_within_category(
    guild: discord.Guild,
    channel: discord.abc.GuildChannel,
    info: dict
) -> None:
    """
    Try best-effort precise placement:
      1) If after_id exists and is still a sibling of same type in target category, place ch before it.
      2) Else clamp to saved index among siblings of same type.
      Always sync permission overwrites to the target category (if any).
    """
    parent = guild.get_channel(info.get("parent_id")) if info.get("parent_id") else None
    ch_type = info.get("type") or _ctype(channel)

    # Step 1: move to the right category first, syncing perms if category exists
    try:
        if parent:
            await channel.edit(category=parent, sync_permissions=True)  # <- inherit original category perms
        else:
            await channel.edit(category=None)  # no category to sync with
    except Exception:
        # If we can't move category, bail out
        return

    # Give Discord a beat to apply the category move before adjusting position
    await asyncio.sleep(0.2)

    # Build sibling list of the same type (excluding this channel)
    siblings = _same_type_siblings(parent, ch_type, exclude_id=channel.id)

    # 1) Try "place before remembered next sibling"
    after_id = info.get("after_id")
    if after_id:
        target = next((c for c in siblings if c.id == after_id), None)
        if target:
            try:
                await channel.edit(position=target.position)
                return
            except Exception:
                pass  # fall through to clamped index

    # 2) Fallback: clamp to saved index among same-type siblings
    saved_pos = int(info.get("position", 0))
    idx = max(0, min(saved_pos, len(siblings)))  # insertion index among siblings without self

    try:
        if not siblings:
            await channel.edit(position=0)
            return

        if idx == len(siblings):
            last_pos = siblings[-1].position
            await channel.edit(position=last_pos + 1)
        else:
            await channel.edit(position=siblings[idx].position)
    except Exception:
        pass

async def restore_to_original(guild: discord.Guild, channel: discord.abc.GuildChannel) -> None:
    info = await original_place(channel.id)
    try:
        if info:
            await _restore_position_within_category(guild, channel, info)
        else:
            # no info; at least pull it out of Archive
            await channel.edit(category=None)
    except Exception:
        pass
