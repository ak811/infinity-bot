from __future__ import annotations
import discord
from typing import Dict, List, Tuple
from configs.config_roles import ALMIGHTY_ROLE_ID, LOOT_AND_LEGENDS_ROLES, MEMBER_ROLE_ID, IN_JAIL_ROLE_ID
from .constants import CATEGORY_ORDER, EXCLUDED_ROLE_ID
from .categorize import categorize_role
from .formatting import chunk_lines, add_field_safely, ensure_capacity, send_embed

async def show_roles(ctx):
    guild: discord.Guild = ctx.guild
    members = [m for m in guild.members if not m.bot]

    loot_xp_map = {rid: min_xp for rid, min_xp, _ in LOOT_AND_LEGENDS_ROLES}
    loot_role_ids = set(loot_xp_map) | {MEMBER_ROLE_ID}

    level_roles: List[Tuple[discord.Role, int]] = []
    community_roles: List[Tuple[discord.Role, int]] = []

    for role in guild.roles:
        if role.id in {ALMIGHTY_ROLE_ID, EXCLUDED_ROLE_ID} or role.is_default():
            continue
        count = sum(1 for m in members if role in m.roles)
        (level_roles if role.id in loot_role_ids else community_roles).append((role, count))

    level_roles.sort(key=lambda x: x[0].position, reverse=True)
    community_roles.sort(key=lambda x: x[0].position, reverse=True)

    level_lines: List[str] = []
    for role, count in level_roles:
        xp_bit = f" (**{loot_xp_map[role.id]:,} XP**)" if role.id in loot_xp_map else ""
        level_lines.append(f"{role.mention} — {count} member{'s' if count != 1 else ''}{xp_bit}")

    buckets: Dict[str, List[str]] = {}
    jail_line = None  # track jail entry to append last in Badges

    for role, count in community_roles:
        cat = categorize_role(role.name)

        # Capture jail line but don't insert yet
        if role.id == IN_JAIL_ROLE_ID:
            jail_line = f"{role.mention} — {count} member{'s' if count != 1 else ''}"
            cat = "🏅 Badges"  # ensure it lives under Badges

        if not cat:
            continue

        # Add all non-jail items normally
        if role.id != IN_JAIL_ROLE_ID:
            buckets.setdefault(cat, []).append(
                f"{role.mention} — {count} member{'s' if count != 1 else ''}"
            )

    # Append the jail item LAST inside Badges
    if jail_line:
        buckets.setdefault("🏅 Badges", []).append(jail_line)

    # ✅ Compute ordered AFTER buckets are finalized so it's always defined
    ordered = [c for c in CATEGORY_ORDER if c in buckets] + [c for c in buckets if c not in CATEGORY_ORDER]

    embeds: List[discord.Embed] = []
    current = discord.Embed(title="📋 Server Role Stats", color=discord.Color.blue())

    if level_lines:
        chunks = list(chunk_lines(level_lines))
        for i, chunk in enumerate(chunks, start=1):
            current = ensure_capacity(embeds, current)
            suffix = f" ({i}/{len(chunks)})" if len(chunks) > 1 else ""
            add_field_safely(current, f"🏆 Level Roles{suffix}", chunk)

    for cat in ordered:
        chunks = list(chunk_lines(buckets.get(cat, [])))
        for i, chunk in enumerate(chunks, start=1):
            current = ensure_capacity(embeds, current)
            suffix = f" ({i}/{len(chunks)})" if len(chunks) > 1 else ""
            add_field_safely(current, f"{cat}{suffix}", chunk)

    if len(current.fields) > 0 or not embeds:
        embeds.append(current)

    for e in embeds:
        await send_embed(ctx, e)
