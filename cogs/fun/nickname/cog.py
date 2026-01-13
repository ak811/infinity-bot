# cogs/nickname/cog.py
from discord.ext import commands
import discord

from .service import apply_suffix, reset_suffix, member_display_base
from .embeds import nickname_help_embed, success_embed, info_embed, error_embed

NICKNAME_GROUP_NAME = "nickname"


class XPNicknameCog(commands.Cog, name="Nickname"):
    """Self-service nickname helpers: show status, reset, and add suffix parts (with embeds & emojis)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(
        name=NICKNAME_GROUP_NAME,
        invoke_without_command=True,
        help="Show your current display name and nickname commands.",
    )
    async def nickname_group(self, ctx: commands.Context):
        """
        Embed output with current display and quick help (emoji-enhanced).
        """
        member: discord.Member = ctx.author  # self-only per spec
        display = member_display_base(member)
        await ctx.send(embed=nickname_help_embed(member, display))

    @nickname_group.command(name="reset", help="Remove any nickname XP/level suffix.")
    async def nickname_reset(self, ctx: commands.Context):
        member: discord.Member = ctx.author
        changed = await reset_suffix(member)
        if changed is None:
            await ctx.send(embed=info_embed(member, "Nothing to reset", "No recognized suffix was present."))
        else:
            await ctx.send(embed=success_embed(member, "Nickname reset", changed))

    @nickname_group.command(name="addxp", help="Append only the XP part (e.g., ' | 309/500 XP').")
    async def nickname_addxp(self, ctx: commands.Context):
        member: discord.Member = ctx.author
        changed = await apply_suffix(member, "xp")
        if changed is None:
            await ctx.send(embed=info_embed(member, "No change", "Your nickname already matches the XP part."))
        else:
            await ctx.send(embed=success_embed(member, "XP part added", changed))

    @nickname_group.command(name="addlevel", help="Append only the Level part (e.g., ' | L6').")
    async def nickname_addlevel(self, ctx: commands.Context):
        member: discord.Member = ctx.author
        changed = await apply_suffix(member, "level")
        if changed is None:
            await ctx.send(embed=info_embed(member, "No change", "Your nickname already matches the Level part."))
        else:
            await ctx.send(embed=success_embed(member, "Level part added", changed))

    @nickname_group.command(name="addboth", help="Append full suffix (e.g., ' | L6 • 309/500 XP').")
    async def nickname_addboth(self, ctx: commands.Context):
        member: discord.Member = ctx.author
        changed = await apply_suffix(member, "full")
        if changed is None:
            await ctx.send(embed=info_embed(member, "No change", "Your nickname already has the full suffix."))
        else:
            await ctx.send(embed=success_embed(member, "Full suffix added", changed))


async def setup(bot: commands.Bot):
    await bot.add_cog(XPNicknameCog(bot))
