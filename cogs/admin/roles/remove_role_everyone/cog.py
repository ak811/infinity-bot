from __future__ import annotations
import discord
from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class RemoveRoleEveryoneCog(commands.Cog):
    """sudo_remove_role_everyone <role_id> — Remove role from all members that have it."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_remove_role_everyone")
    @commands.has_permissions(administrator=True)
    async def sudo_remove_role_everyone(self, ctx: commands.Context, role_id: int):
        role = ctx.guild.get_role(role_id)
        if role is None:
            await ctx.send(f"🙅 Role with ID `{role_id}` not found.")
            return

        removed, failed = 0, []
        for m in list(role.members):
            try:
                await m.remove_roles(role, reason=f"Bulk remove by {ctx.author}")
                removed += 1
            except Exception as e:
                failed.append(m.display_name)
                log.exception("Failed to remove role", exc_info=e)

        msg = f"Removed **{role.mention}** from {removed} members."
        if failed:
            msg += f"\nFailed: {', '.join(failed)}"
        await ctx.send(msg)

async def setup(bot: commands.Bot):
    await bot.add_cog(RemoveRoleEveryoneCog(bot))
