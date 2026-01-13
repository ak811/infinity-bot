# cogs/stats/logging/delete/__init__.py
from discord.ext import commands
from .cog import DeleteLoggingCog

async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteLoggingCog(bot))
