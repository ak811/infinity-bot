# cogs/stats/logging/reactions/__init__.py
from discord.ext import commands
from .cog import ReactionsLoggingCog

async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionsLoggingCog(bot))
