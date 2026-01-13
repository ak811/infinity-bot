from __future__ import annotations
import discord
from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class AddRoleEveryoneCog(commands.Cog):
    """sudo_add_role_everyone <role_id> — Add a role to all non-bot members missing it."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_add_role_everyone")
    @commands.has_permissions(administrator=True)
    async def sudo_add_role_everyone(self, ctx: commands.Context, role_id: int):
        role = ctx.guild.get_role(role_id)
        if role is None:
            await ctx.send(f"🙅 Role with ID `{role_id}` not found.")
            return

        added, failed = 0, []
        for m in ctx.guild.members:
            if m.bot or role in m.roles:
                continue
            try:
                await m.add_roles(role, reason=f"Bulk add by {ctx.author}")
                added += 1
            except Exception as e:
                failed.append(m.display_name)
                log.exception("Failed to add role", exc_info=e)

        msg = f"Added **{role.mention}** to {added} members."
        if failed:
            msg += f"\nFailed: {', '.join(failed)}"
        await ctx.send(msg)

async def setup(bot: commands.Bot):
    await bot.add_cog(AddRoleEveryoneCog(bot))
