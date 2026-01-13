# cogs/voice_state_updates/move_active_vc.py
from __future__ import annotations

import logging, asyncio
import discord
from configs.config_channels import (
    JOIN_TO_CREATE_CHANNEL_ID,
    SOLO_CHANNEL_ID,
    DUO_CHANNEL_ID,
    TRIO_CHANNEL_ID,
    QUAD_CHANNEL_ID,
    HIVE_CHANNEL_ID,
    CREW_CHANNEL_ID,
    PARTY_CHANNEL_ID,
)

EXCLUDED_VC_IDS = {
    int(SOLO_CHANNEL_ID),
    int(DUO_CHANNEL_ID),
    int(TRIO_CHANNEL_ID),
    int(QUAD_CHANNEL_ID),
    int(HIVE_CHANNEL_ID),
    int(CREW_CHANNEL_ID),
    int(PARTY_CHANNEL_ID),
}

async def move_active_vc(vc: discord.VoiceChannel | None) -> None:
    """
    If a voice channel has members, move it directly below the Join-to-Create
    channel, in the same category as Join-to-Create, and sync perms when moving
    categories.
    """
    if vc is None:
        return

    # Skip Join-to-Create channel and excluded ones
    if int(vc.id) == int(JOIN_TO_CREATE_CHANNEL_ID) or int(vc.id) in EXCLUDED_VC_IDS:
        logging.debug(f"[move_active_vc] Skipping excluded VC '{vc.name}' ({vc.id})")
        return

    guild = vc.guild
    join_to_create = guild.get_channel(int(JOIN_TO_CREATE_CHANNEL_ID))
    if not isinstance(join_to_create, (discord.VoiceChannel, discord.StageChannel)):
        logging.error("[move_active_vc] Missing required channel: JOIN_TO_CREATE_CHANNEL_ID")
        return

    join_cat = join_to_create.category
    if join_cat is None:
        logging.error("[move_active_vc] Join-to-Create channel has no category")
        return

    if len(vc.members) >= 1:
        try:
            logging.info(f"[move_active_vc] Moving active VC '{vc.name}' under Join-to-Create")

            # Step 1: if category differs, move and sync perms
            if vc.category is None or vc.category.id != join_cat.id:
                await vc.edit(category=join_cat, sync_permissions=True)
                # Give Discord a moment to apply the category move before positioning
                await asyncio.sleep(0.2)

            # Step 2: position just below the Join-to-Create channel
            await vc.edit(position=join_to_create.position + 1)

        except discord.Forbidden:
            logging.error(f"[move_active_vc] Missing permissions to move/sync '{vc.name}'")
        except Exception as e:
            logging.error(f"[move_active_vc] Error moving '{vc.name}': {e}")
    else:
        logging.debug(f"[move_active_vc] '{vc.name}' is empty; skipping move.")
