# cogs/stats/logging/roles/cog.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
from types import SimpleNamespace

import discord
from discord.ext import commands

from configs.config_channels import LOGS_CHANNEL_ID
from configs.config_logging import logging
from configs.helper import send_as_webhook  # webhook-only sender


def _fmt_roles(roles: Iterable[discord.Role]) -> str:
    # Skip @everyone/default role
    listed = [role.mention for role in roles if not role.is_default()]
    return ", ".join(listed) if listed else "*(none)*"


class RolesLoggingCog(commands.Cog):
    """Logs role additions/removals on members via webhook (key='roles')."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _send_roles_webhook(
        self,
        title: str,
        member: discord.Member,
        body_name: str,
        body_value: str,
        color: int,
    ) -> None:
        try:
            target = self.bot.get_channel(LOGS_CHANNEL_ID) or await self.bot.fetch_channel(LOGS_CHANNEL_ID)
            if not isinstance(target, (discord.TextChannel, discord.Thread)):
                logging.warning("[RolesLog] LOGS_CHANNEL_ID is not a text channel/thread.")
                return

            embed = discord.Embed(
                title=title,
                description=f"Member: {member.mention}",
                color=color,
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(name=body_name, value=body_value, inline=False)

            # Faux ctx with .channel for send_as_webhook
            faux_ctx = SimpleNamespace(guild=getattr(target, "guild", None), channel=target, author=member)

            # Persona key is 'roles'
            await send_as_webhook(faux_ctx, "roles", embed=embed)

        except Exception as e:
            logging.warning(f"[RolesLog] Failed to send roles webhook: {e}")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        try:
            if before.guild is None:
                return

            before_set = set(before.roles)
            after_set = set(after.roles)

            added = after_set - before_set
            removed = before_set - after_set

            if not added and not removed:
                return

            if added:
                await self._send_roles_webhook(
                    title="✅ Roles Added",
                    member=after,
                    body_name="Added",
                    body_value=_fmt_roles(added),
                    color=discord.Color.green().value,
                )

            if removed:
                await self._send_roles_webhook(
                    title="❎ Roles Removed",
                    member=after,
                    body_name="Removed",
                    body_value=_fmt_roles(removed),
                    color=discord.Color.red().value,
                )

        except Exception as e:
            logging.warning(f"[RolesLog] Exception in on_member_update: {e}")
