from __future__ import annotations

import discord
from discord.ext import commands

from .helpers import (
    build_public_commands_embeds,
    build_sudo_commands_embeds,
    add_slash_commands_section,  # optional
)

class CommandsDirectoryCog(commands.Cog):
    """
    Dynamic command directory:
      • !commands — lists public (non-sudo) prefix commands, grouped into neat emoji categories
      • !sudo_commands — lists commands whose name starts with 'sudo', grouped into neat emoji categories
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="commands", aliases=["c"])
    async def commands_list(self, ctx: commands.Context):
        """
        Lists all available public commands as categorized embeds.
        Allowed in any channel.
        """
        prefix = getattr(ctx, "clean_prefix", None) or "!"
        embeds = build_public_commands_embeds(self.bot, prefix)

        # (Optional) add slash commands to the LAST page:
        # add_slash_commands_section(embeds[-1], self.bot)

        for e in embeds:
            await ctx.send(embed=e)

    @commands.command(name="sudo_commands")
    async def sudo_commands_list(self, ctx: commands.Context):
        """
        Lists sudo/admin commands (names starting with 'sudo') as categorized embeds.
        Allowed in any channel.
        Shows the warning text only if the caller is NOT an administrator.
        """
        prefix = getattr(ctx, "clean_prefix", None) or "!"
        is_admin = bool(ctx.guild and ctx.author.guild_permissions.administrator)
        embeds = build_sudo_commands_embeds(self.bot, prefix, show_admin_warning=not is_admin)

        # (Optional) include slash commands here as well
        # add_slash_commands_section(embeds[-1], self.bot)

        for e in embeds:
            await ctx.send(embed=e)

async def setup(bot: commands.Bot):
    await bot.add_cog(CommandsDirectoryCog(bot))
