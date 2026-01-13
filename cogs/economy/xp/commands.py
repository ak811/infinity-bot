# cogs/xp/commands.py
from __future__ import annotations

import discord
from discord.ext import commands

from .service import get_user_activity_breakdown, get_total_xp
from .weights import ACTIVITY_WEIGHTS

# --- optional level helpers ---------------------------------------------------
try:
    from xp.levels import get_level_info as _get_level_info  # type: ignore[attr-defined]
except Exception:
    _get_level_info = None  # type: ignore[assignment]

EMOJIS: dict[str, str] = {
    "Messages": "💬",
    "VC": "🎙️",
    "Bump": "🛎️",
    "Add Reaction": "🎈",
    "Receive Reaction": "❤️",
    "Other": "🧩",
    "Tree": "🌳",
    "Idiom Theater": "🎭",
    "Word Dojo": "🗽",
    "Grammar Guru": "🤓",
    "Flag Frenzy": "🚩",
}

VISIBLE_CATEGORIES: set[str] = {
    "Messages",
    "VC",
    "Bump",
    "Add Reaction",
    "Receive Reaction",
    "Other",
    "Tree",
}

CONSOLIDATE_TO: str = "Messages"

PREFERRED_ORDER: list[str] = [
    "Messages",
    "VC",
    "Add Reaction",
    "Receive Reaction",
    "Tree",
    "Bump",
    "Other",
]

RAW_TO_FRIENDLY: dict[str, str] = {
    "messages": "Messages",
    "message length": "Messages",
    "message_length": "Messages",
    "link/media": "Messages",
    "vc_seconds": "VC",
    "bump": "Bump",
    "add_reaction": "Add Reaction",
    "receive_reaction": "Receive Reaction",
    "other": "Other",
    "tree": "Tree",
    "idiom quiz": "Idiom Theater",
    "idiom_quiz": "Idiom Theater",
    "idiom": "Idiom Theater",
    "word quiz": "Word Dojo",
    "word_quiz": "Word Dojo",
    "word": "Word Dojo",
    "grammar quiz": "Grammar Guru",
    "grammar_quiz": "Grammar Guru",
    "grammar": "Grammar Guru",
    "flag hourly quiz": "Flag Frenzy",
    "flag_hourly_quiz": "Flag Frenzy",
    "flag": "Flag Frenzy",
}

def _normalize_key(k: str) -> str:
    return (k or "").strip().lower()

def _aggregate_contribs(xp_map: dict[str, float]) -> list[tuple[str, float]]:
    contribs: dict[str, float] = {}

    def add(key: str, amt: float):
        contribs[key] = contribs.get(key, 0.0) + amt

    for raw_key, raw_amt in (xp_map or {}).items():
        weight = float(ACTIVITY_WEIGHTS.get(raw_key, 1.0))
        contrib = float(raw_amt) * weight

        nk = _normalize_key(raw_key)
        friendly = RAW_TO_FRIENDLY.get(nk)
        if friendly is None:
            friendly = "Other"
        if friendly not in VISIBLE_CATEGORIES:
            friendly = CONSOLIDATE_TO

        add(friendly, contrib)

    for cat in VISIBLE_CATEGORIES:
        contribs.setdefault(cat, 0.0)

    return list(contribs.items())

def _bar(current: float, max_val: float, width: int = 12) -> str:
    if max_val <= 0:
        return "░" * width
    filled = max(1, round((current / max_val) * width)) if current > 0 else 0
    filled = min(filled, width)
    return "█" * filled + "░" * (width - filled)

def _sort_items(items: list[tuple[str, float]]) -> list[tuple[str, float]]:
    order_index = {name: i for i, name in enumerate(PREFERRED_ORDER)}
    fallback_index = order_index.get("Other", len(PREFERRED_ORDER))
    def key_fn(item: tuple[str, float]):
        name, contrib = item
        idx = order_index.get(name, fallback_index - 1)
        return (idx, -contrib, name.lower())
    return sorted(items, key=key_fn)

def _level_badge(user_id: int, total_xp: int) -> str | None:
    if callable(_get_level_info):
        try:
            info = _get_level_info(user_id)
            level = int(info.get("level"))
            cur = int(info.get("current_xp"))
            nxt = int(info.get("next_level_xp"))
            if level >= 0 and nxt > 0:
                return f" | L{level} • {cur:,}/{nxt:,} XP"
        except Exception:
            pass
    return None

def _display_title_for(target: discord.Member, total_xp: int) -> str:
    base = target.display_name
    badge = _level_badge(target.id, total_xp)
    if badge:
        return f"📊 Activities You Gained XP From — {base}{badge}"
    return f"📊 Activities You Gained XP From — {base}"

def _fmt_activity_table(xp_map: dict[str, float]) -> str:
    items = _aggregate_contribs(xp_map)
    if not items:
        return "*No activity recorded yet.*"
    items = _sort_items(items)
    max_contrib = max(c for _, c in items) if items else 0.0

    lines = []
    for name, contrib in items:
        if name not in VISIBLE_CATEGORIES:
            continue
        emoji = EMOJIS.get(name, "•")
        bar = _bar(contrib, max_contrib)
        lines.append(f"{emoji} **{name}** │ {bar} +{int(contrib):,} XP")
    return "\n".join(lines)


class XPCommands(commands.Cog):
    """`!xp` command to show weighted activity breakdown."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="xp",
        help="Show where your XP comes from. Usage: !xp or !xp @user",
    )
    @commands.guild_only()
    async def xp_cmd(self, ctx: commands.Context, member: discord.Member | None = None):
        target = member or ctx.author

        xp_map = get_user_activity_breakdown(target.id) or {}
        total = int(get_total_xp(target.id) or 0)

        embed = discord.Embed(
            title=_display_title_for(target, total),
            description=_fmt_activity_table(xp_map),
            color=discord.Color.teal(),
        )
        embed.set_footer(text=f"Total XP: {total:,}")
        await ctx.send(embed=embed)
