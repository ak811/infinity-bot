from __future__ import annotations
import logging
from typing import Iterable

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class AddMemberRoleEveryoneExceptVIPs(commands.Cog):
    """
    !sudo_add_member_role_everyone_except_vips <role_id> <vip_role_id ...>
    Add <role_id> to all non-bot members who don't already have it,
    excluding anyone who has ANY of the listed VIP roles.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_add_member_role_everyone_except_vips")
    @commands.has_permissions(administrator=True, manage_roles=True)
    @commands.guild_only()
    async def sudo_add_member_role_everyone_except_vips(
        self,
        ctx: commands.Context,
        role_id: int,
        *vip_role_ids: int,
    ):
        guild: discord.Guild = ctx.guild
        assert guild is not None

        target_role = guild.get_role(role_id)
        if target_role is None:
            await ctx.send(f"🙅 Role with ID `{role_id}` not found.")
            return

        if not guild.me.guild_permissions.manage_roles:
            await ctx.send("🙅 I need the **Manage Roles** permission to do that.")
            return

        # The bot can only assign roles lower than its top role.
        if guild.me.top_role <= target_role:
            await ctx.send(
                f"🙅 I can't assign **{target_role.name}** because it's not lower than my top role."
            )
            return

        # Resolve VIP roles (ignore any that aren't found)
        vip_roles = [guild.get_role(rid) for rid in vip_role_ids]
        vip_roles = [r for r in vip_roles if r is not None]

        # Build a set of member IDs to exclude (anyone with any VIP role)
        def members_with_any(roles: Iterable[discord.Role]) -> set[int]:
            s: set[int] = set()
            for r in roles:
                s.update(m.id for m in r.members)
            return s

        excluded_ids = members_with_any(vip_roles) if vip_roles else set()

        added = 0
        failed = []

        # Iterate all guild members
        for member in guild.members:
            # Skip bots, already has role, or excluded as VIP
            if member.bot or target_role in member.roles or member.id in excluded_ids:
                continue

            # Extra safety: bot cannot modify members with >= bot's top role
            if member.top_role >= guild.me.top_role and member != guild.owner:
                failed.append(member.display_name)
                log.info(
                    "Skipping %s due to role hierarchy (member.top_role >= bot.top_role)",
                    member,
                )
                continue

            try:
                await member.add_roles(
                    target_role,
                    reason=f"Bulk add (exclude VIPs) by {ctx.author} [{ctx.author.id}]",
                )
                added += 1
            except Exception as e:
                failed.append(member.display_name)
                log.exception("Failed to add role to %s", member, exc_info=e)

        # Build response
        vip_info = (
            "none"
            if not vip_roles
            else ", ".join(r.mention for r in vip_roles)
        )
        msg = (
            f"✅ Added **{target_role.mention}** to **{added}** member(s).\n"
            f"🚫 Excluded VIP roles: {vip_info}."
        )

        if failed:
            # Keep message tidy if there are many failures
            failed_preview = ", ".join(failed[:20])
            extra = "" if len(failed) <= 20 else f" …and {len(failed) - 20} more"
            msg += f"\n⚠️ Failed for: {failed_preview}{extra}"

        await ctx.send(msg)


async def setup(bot: commands.Bot):
    await bot.add_cog(AddMemberRoleEveryoneExceptVIPs(bot))
