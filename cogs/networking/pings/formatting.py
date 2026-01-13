# cogs/networking/pings/formatting.py
from __future__ import annotations
from typing import Dict, List
import discord

def _fmt_member_ref(guild: discord.Guild, uid: int):
    member = guild.get_member(uid)
    if member:
        return member.mention, member.display_name
    return f"<@{uid}>", f"User Left ({uid})"

def build_stats_lines(entry: Dict[str, int], guild: discord.Guild, limit: int = 10) -> List[str]:
    top = sorted(entry.items(), key=lambda x: x[1], reverse=True)[:limit]
    lines: List[str] = []
    for idx, (uid, count) in enumerate(top, start=1):
        mention, name = _fmt_member_ref(guild, int(uid))
        lines.append(f"**`#{idx}`** {mention} ・ *{name}* — **{count}** pings")
    return lines

def build_server_top_lines(data: Dict[str, int], guild: discord.Guild, limit: int = 10) -> List[str]:
    top = sorted(data.items(), key=lambda x: x[1], reverse=True)[:limit]
    lines: List[str] = []
    for idx, (uid, count) in enumerate(top, start=1):
        mention, name = _fmt_member_ref(guild, int(uid))
        lines.append(f"**`#{idx}`** {mention} ・ *{name}* — **{count}** pings")
    return lines
