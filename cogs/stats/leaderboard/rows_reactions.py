# cogs/leaderboard/rows_reactions.py
from __future__ import annotations

import discord
from utils.utils_json import load_json

REACTIONS_GIVEN_FILE = "database/reaction_given.json"
REACTIONS_RECEIVED_FILE = "database/reaction_received.json"


def _count(maplike, uid: str) -> int:
    try:
        return int(maplike.get(uid, 0))
    except (TypeError, ValueError):
        return 0


def make_reactions_compute_fn(file_path: str):
    """Returns compute(user_id, now, guild) for a simple {uid: count} JSON."""
    def compute(user_id: int | str, _now, guild: discord.Guild):
        uid = str(user_id)
        data = load_json(file_path, default_value={})
        cnt = _count(data, uid)
        if cnt <= 0:
            return None
        member = guild.get_member(int(uid))
        if not member or member.bot:
            return None
        return (member, cnt)
    return compute


def reactions_sort_key(row):  # (member, cnt)
    return (row[1],)


def make_format_reactions_row(label_emoji: str):
    def fmt(rank: int, row):
        member, cnt = row
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
        return f"{medal} {member.mention} *(`{member.display_name}`)* — {label_emoji} **{cnt}**"
    return fmt
