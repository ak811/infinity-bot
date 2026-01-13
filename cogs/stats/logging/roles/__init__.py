# cogs/stats/logging/roles/__init__.py
from discord.ext import commands
from .cog import RolesLoggingCog

async def setup(bot: commands.Bot):
    await bot.add_cog(RolesLoggingCog(bot))
