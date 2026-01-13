from __future__ import annotations
import discord
from typing import Union
from configs.config_roles import LOOT_AND_LEGENDS_ROLES, LEVEL_UP_REWARDS, MEMBER_ROLE_ID
from configs.config_logging import logging

from cogs.economy.xp.service import get_total_xp as get_xp
from cogs.economy.coin.service import update_coins
from cogs.economy.orb.service import update_orbs
from cogs.economy.star.service import update_stars
from .rewards import announce_role_upgrade
import asyncio
from collections import defaultdict
user_locks = defaultdict(asyncio.Lock)

def _min_xp(rt): return getattr(rt, "min_xp", rt[1])
def _role_id(rt): return getattr(rt, "role_id", rt[0])

async def assign_role_based_on_xp(member: Union[discord.Member, discord.User], guild: discord.Guild) -> None:
    if isinstance(member, discord.User):
        try:
            member = guild.get_member(member.id) or await guild.fetch_member(member.id)
        except discord.NotFound:
            return
    if member.bot:
        return

    async with user_locks[member.id]:
        try:
            total_xp = get_xp(member.id)
        except Exception as e:
            logging.info(f"XP fetch error for {member.id}: {e}")
            return

        eligible = [rt for rt in LOOT_AND_LEGENDS_ROLES if total_xp >= _min_xp(rt)]
        if not eligible:
            return

        best = max(eligible, key=_min_xp)
        new_role = guild.get_role(_role_id(best))
        if not new_role:
            return

        # Which L&L roles does the user currently have?
        member_role_ids = {r.id for r in member.roles}
        ll_roles_on_member = [rt for rt in LOOT_AND_LEGENDS_ROLES if _role_id(rt) in member_role_ids]

        # If they already have >= best tier, still clean up any lower tiers lingering.
        already_at_or_above_best = any(_min_xp(rt) >= _min_xp(best) for rt in ll_roles_on_member)
        if already_at_or_above_best:
            # remove any lower L&L tiers (keep the highest one(s))
            roles_to_remove = [
                guild.get_role(_role_id(rt))
                for rt in ll_roles_on_member
                if _role_id(rt) != _role_id(best)
            ]
            roles_to_remove = [r for r in roles_to_remove if r]
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason="XP tier cleanup (exclusive L&L tiers)")
                except discord.Forbidden:
                    pass
            return  # nothing else to do

        # They are upgrading: remove "newcomer" (if present), add new tier, then remove old tiers.
        newcomer = guild.get_role(MEMBER_ROLE_ID)
        if newcomer and newcomer in member.roles:
            try:
                await member.remove_roles(newcomer, reason="XP tier upgrade (removed newcomer)")
            except discord.Forbidden:
                pass

        # 1) Add the new tier
        await member.add_roles(new_role, reason="Reached XP threshold")

        # 2) Remove any previously held L&L tiers (exclusivity)
        roles_to_remove = [
            guild.get_role(_role_id(rt))
            for rt in ll_roles_on_member
            if _role_id(rt) != new_role.id
        ]
        roles_to_remove = [r for r in roles_to_remove if r]
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="XP tier upgrade (exclusive L&L tiers)")
            except discord.Forbidden:
                pass

        # Rewards
        idx = LOOT_AND_LEGENDS_ROLES.index(best)
        dollars, orbs, stars = rewards = LEVEL_UP_REWARDS.get(idx, (0, 0, 0))
        try:
            update_coins(member.id, dollars, "Level Up Rewards")
            update_orbs(member.id, orbs, "Level Up Rewards")
            update_stars(member.id, stars, "Level Up Rewards")
        except Exception as e:
            logging.info(f"Reward error for {member.id}: {e}")

        await announce_role_upgrade(member, new_role, rewards)
