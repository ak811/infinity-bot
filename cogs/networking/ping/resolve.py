# cogs/ping/resolve.py
from __future__ import annotations
import re
import unicodedata
import discord
from typing import Optional, Tuple, List
from .config import PINGABLE_EXTRA_ROLE_IDS
from configs.config_roles import LOOT_AND_LEGENDS_ROLES

MENTION_RE = re.compile(r"<@&(\d+)>")

def _normalize(s: str) -> str:
    if s is None:
        return ""
    s = s.replace("–", "-").replace("—", "-").replace("\\", "/")
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9/\+\-\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _score(query_norm: str, role_norm: str) -> int:
    if query_norm == role_norm:
        return 100
    if role_norm.startswith(query_norm) or role_norm.endswith(query_norm) or query_norm in role_norm:
        return 80
    if query_norm.startswith(role_norm) or query_norm.endswith(role_norm):
        return 70
    return 0

def _ladder_role_ids() -> set[int]:
    # include both ladder & extra-allowed roles for sorting preference
    return {rid for rid, *_ in LOOT_AND_LEGENDS_ROLES} | set(PINGABLE_EXTRA_ROLE_IDS)

async def resolve_role(guild: discord.Guild, query: str) -> Optional[discord.Role]:
    if not query:
        return None

    # 1) Mention
    m = MENTION_RE.search(query)
    if m:
        rid = int(m.group(1))
        r = guild.get_role(rid)
        if r:
            return r

    # 2) Raw ID
    if query.isdigit():
        r = guild.get_role(int(query))
        if r:
            return r

    # 3) Exact name (case-sensitive first)
    for r in guild.roles:
        if r.name == query:
            return r

    # 4) Fuzzy by normalization
    qn = _normalize(query)
    scored: List[Tuple[discord.Role, int, bool]] = []
    ladder_ids = _ladder_role_ids()
    for r in guild.roles:
        rn = _normalize(r.name)
        sc = _score(qn, rn)
        if sc > 0:
            scored.append((r, sc, r.id in ladder_ids))

    if not scored:
        return None

    # Prefer higher score, then ladder members, then higher position
    scored.sort(key=lambda t: (t[1], t[2], t[0].position), reverse=True)
    return scored[0][0]
