# cogs/tree/logic.py
from __future__ import annotations

import re
from typing import Iterable, Tuple, List, Optional
import discord

from configs.helper import send_as_webhook

from cogs.economy.orb.service import update_orbs
from cogs.economy.xp.service import update_xp

WATERING_PHRASE = "for watering the tree!"
USER_MENTION_RE = re.compile(r"<@!?(\d+)>")
RELATIVE_TS_RE = re.compile(r"<t:(\d+):R>")  # unix seconds in embed

def extract_watering_user_id(description: str) -> Optional[int]:
    if WATERING_PHRASE not in description:
        return None
    m = USER_MENTION_RE.search(description)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

def extract_target_unix(description: str) -> Optional[int]:
    m = RELATIVE_TS_RE.search(description)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None

async def award_orb_and_announce(channel: discord.TextChannel, user: discord.User | discord.Member) -> None:
    update_orbs(user.id, 1, "tree")
    update_xp(user.id, 5, "tree")

    embed = discord.Embed(
        title="🌳 Tree Watered! 🌊",
        description=f"🎯 {user.mention} `{getattr(user, 'display_name', user.name)}` has earned **1 Orb** 🔮 for watering the tree!",
        color=discord.Color.green(),
    )
    await send_as_webhook(channel, "grow_a_tree", embed=embed)
