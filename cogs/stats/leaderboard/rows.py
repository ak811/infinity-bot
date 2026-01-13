# cogs/leaderboard/rows.py
from __future__ import annotations

import discord
from configs.config_roles import LOOT_AND_LEGENDS_ROLES, MEMBER_ROLE_ID
from cogs.economy.coin.service import get_total_coins
from cogs.economy.orb.service import get_total_orbs
from cogs.economy.diamond.service import get_total_diamonds
from cogs.economy.star.service import get_total_stars
from cogs.economy.dollar.service import get_total_dollars

from cogs.economy.xp.service import get_total_xp as svc_get_total_xp


def _highest_ll_role(member: discord.Member, guild: discord.Guild):
    role_rank = -1
    highest_role = None
    for idx, (role_id, _, _) in enumerate(LOOT_AND_LEGENDS_ROLES):
        role = guild.get_role(role_id)
        if role and role in member.roles and idx > role_rank:
            role_rank = idx
            highest_role = role
    if highest_role is None:
        highest_role = discord.utils.get(guild.roles, id=MEMBER_ROLE_ID)
    return highest_role, role_rank


def compute_coins_row(user_id: int | str, _current_time, guild: discord.Guild):
    uid = int(user_id)
    total_xp = svc_get_total_xp(uid)
    diamonds = get_total_diamonds(uid)

    member = guild.get_member(uid)
    if not member or member.bot:
        return None
    if total_xp == 0 and diamonds == 0:
        return None

    coins = get_total_coins(uid)
    orbs = get_total_orbs(uid)
    stars = get_total_stars(uid)
    role, role_rank = _highest_ll_role(member, guild)

    # NEW: total USD (rounded to cents by default)
    usd_total = get_total_dollars(uid)

    # Return usd_total as the last element to keep existing indices stable
    return (member, total_xp, coins, orbs, stars, diamonds, role, role_rank, usd_total)


def format_coins_row(rank: int, row):
    """
    Pretty-prints a row into a single string for an embed field.
    """
    member, total_xp, coins, orbs, stars, diamonds, role, _, usd_total = row
    medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
    role_text = role.mention if role else ""
    # show display name only, in italics + monospace
    name_bit = f"*(`{member.display_name}`)*"
    return (
        f"{medal} {member.mention} {name_bit} {role_text} "
        f"🌟 {int(total_xp)} XP  "
        f"🪙 {coins}  🔮 {orbs}  ⭐ {stars}  💎 {diamonds}  "
        f"‌ ‌**💵 ${usd_total:,.2f}**"
    )


# Keep the sort key unchanged (role rank, then XP, then coins)
coins_sort_key = lambda row: (row[7], row[1], row[2])
