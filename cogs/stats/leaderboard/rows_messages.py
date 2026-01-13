# cogs/leaderboard/rows_messages.py
from __future__ import annotations

import discord
from utils.utils_json import load_json

MESSAGE_LEADERBOARD_FILE = "database/leaderboard_messages.json"


def _normalize_count(maplike, uid: str) -> int:
    v = maplike.get(uid, 0)
    if isinstance(v, dict):
        v = v.get("messages") or v.get("count") or v.get("total") or 0
    try:
        return int(v)
    except (TypeError, ValueError):
        return 0


def make_messages_compute_fn(file_path: str = MESSAGE_LEADERBOARD_FILE):
    def compute(user_id: int | str, _now, guild: discord.Guild):
        uid = str(user_id)
        data = load_json(file_path, default_value={})
        cnt = _normalize_count(data, uid)
        if cnt <= 0:
            return None
        member = guild.get_member(int(uid))
        if not member or member.bot:
            return None
        return (member, cnt)
    return compute


def messages_sort_key(row):  # (member, cnt)
    return (row[1],)


def format_messages_row(rank: int, row):
    member, cnt = row
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
    return f"{medal} {member.mention} *(`{member.display_name}`)* — **{cnt}** messages"
