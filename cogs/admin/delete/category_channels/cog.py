from __future__ import annotations
import discord
from discord.ext import commands

class DeleteCategoryChannelsCog(commands.Cog):
    """sudo_delete_category_channels <category_id> — Delete all channels in a category."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_delete_category_channels")
    @commands.has_permissions(administrator=True)
    async def sudo_delete_category_channels(self, ctx: commands.Context, category_id: int):
        category = discord.utils.get(ctx.guild.categories, id=category_id)
        if not category:
            await ctx.send("Invalid category ID. Please check and try again.")
            return

        await ctx.send(f"Deleting all channels in `{category.name}`...")
        for ch in list(category.channels):
            try:
                await ch.delete()
                await ctx.send(f"Deleted: **#{ch.name}**")
            except Exception as e:
                await ctx.send(f"Failed to delete {ch.name}: {e}")

        await ctx.send(f"✅ All channels in `{category.name}` have been deleted!")

async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteCategoryChannelsCog(bot))
