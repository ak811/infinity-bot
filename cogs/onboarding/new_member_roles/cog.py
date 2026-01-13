# cogs/new_member_roles/cog.py
from __future__ import annotations

import logging
import discord
from discord.ext import commands

# XP total — keep your original import path
from cogs.economy.xp.service import get_total_xp

# Configs
from configs.config_roles import LOOT_AND_LEGENDS_ROLES  # [(role_id, min_xp, max_xp), ...]
from configs.config_roles import MEMBER_ROLE_ID          # newcomer/basic member role id

log = logging.getLogger(__name__)


async def _restore_or_newcomer_roles(member: discord.Member) -> None:
    """
    If the user has XP, remove newcomer and restore all XP roles up to their tier.
    Otherwise, give only the newcomer role.
    """
    guild = member.guild
    newcomer = guild.get_role(int(MEMBER_ROLE_ID))

    try:
        xp = get_total_xp(member.id) or 0
    except Exception:
        xp = 0

    if xp > 0:
        # Remove newcomer if present
        if newcomer and newcomer in member.roles:
            try:
                await member.remove_roles(newcomer, reason="Re-join: remove newcomer")
            except Exception as e:
                log.error(f"[Join] Could not remove newcomer role from {member.id}: {e}")

        # Grant every role for which xp >= min_xp
        for role_id, min_xp, _max_xp in LOOT_AND_LEGENDS_ROLES:
            if xp >= int(min_xp):
                role = guild.get_role(int(role_id))
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Re-join: restore XP roles")
                    except Exception as e:
                        log.error(f"[Join] Could not add role {role_id} to {member.id}: {e}")
    else:
        # Brand-new user: only newcomer
        if newcomer and newcomer not in member.roles:
            try:
                await member.add_roles(newcomer, reason="New user: assign newcomer")
            except Exception as e:
                log.error(f"[Join] Could not assign newcomer role to {member.id}: {e}")


class NewMemberRolesCog(commands.Cog):
    """Restores XP-based roles (or assigns newcomer) on member join."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_member_join")
    async def on_member_join_listener(self, member: discord.Member):
        if member.bot:
            return
        log.info(f"[Join] New member joined: {member} (ID: {member.id})")
        try:
            await _restore_or_newcomer_roles(member)
        except Exception:
            log.exception(f"[Join] Unexpected error while handling roles for {member.id}")

# Extension entrypoint
async def setup(bot: commands.Bot):
    await bot.add_cog(NewMemberRolesCog(bot))
