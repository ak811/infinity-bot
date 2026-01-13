# cogs/server/help/cog.py
from __future__ import annotations

import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    """
    Provides the custom !help command (overrides discord.py's default help).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx: commands.Context):
        """
        Provides information about the bot.
        """
        embed = discord.Embed(
            title="Infinity Café Bot ☕",
            description="Hey, I'm **Infinity Café Bot**, and I'm here to serve you! 😊",
            color=discord.Color.purple(),
        )
        embed.add_field(
            name="Need Help?",
            value="Use **!commands** to see a full list of my commands!",
            inline=False,
        )
        embed.set_footer(text="Brewed with ❤️ by alex.k")

        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    # remove the default help command so our text command can use the name "help"
    if bot.get_command("help"):
        bot.remove_command("help")
    await bot.add_cog(HelpCog(bot))
