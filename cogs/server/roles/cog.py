from __future__ import annotations
import discord
from discord.ext import commands

from .stats import show_roles
from .search import show_role_members
from .reset import reset_level_roles

class RolesCog(commands.Cog):
    """Roles utilities grouped as commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="roles", aliases=["r"])
    async def roles(self, ctx: commands.Context, *, query: str | None = None):
        # If there’s a query (e.g., mention or name), show members of that role.
        if query and query.strip():
            await show_role_members(ctx, query)
        else:
            await show_roles(ctx)

    @commands.command(name="sudo_roles_members", aliases=["role_members", "rmembers"])
    @commands.has_permissions(administrator=True)
    async def sudo_roles_members(self, ctx: commands.Context, *, query: str):
        await show_role_members(ctx, query)

    @commands.command(name="sudo_roles_reset")
    @commands.has_permissions(administrator=True)
    async def sudo_roles_reset(self, ctx: commands.Context):
        await reset_level_roles(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(RolesCog(bot))
