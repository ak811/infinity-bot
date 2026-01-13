# cogs/ping/__init__.py
from .main import PingCog

async def setup(bot):
    await bot.add_cog(PingCog(bot))
