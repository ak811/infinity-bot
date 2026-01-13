# cogs/leaderboard/rows_vc.py
from __future__ import annotations

import discord
from utils.utils_json import load_json
from configs.config_files import ACTIVITY_DATA_FILE


def _vc_secs(maplike, uid: str) -> float:
    rec = maplike.get(uid) or {}
    xp = rec.get("xp") or {}
    try:
        return float(xp.get("vc_seconds", 0.0))
    except (TypeError, ValueError):
        return 0.0


def make_vc_compute_fn(file_path: str = ACTIVITY_DATA_FILE):
    def compute(user_id: int | str, _now, guild: discord.Guild):
        uid = str(user_id)
        data = load_json(file_path, default_value={})
        secs = _vc_secs(data, uid)
        if secs <= 0:
            return None
        member = guild.get_member(int(uid))
        if not member or member.bot:
            return None
        return (member, int(secs))
    return compute


def vc_sort_key(row):  # (member, secs)
    return (row[1],)


def _fmt_dhms(total: int) -> str:
    d = total // 86400
    h = (total % 86400) // 3600
    m = (total % 3600) // 60
    s = total % 60
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    parts.append(f"{m}m")
    if not d and not h and not m:
        parts.append(f"{s}s")
    return " ".join(parts)


def format_vc_row(rank: int, row):
    member, secs = row
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
    return f"{medal} {member.mention} *(`{member.display_name}`)* — {_fmt_dhms(secs)}"
