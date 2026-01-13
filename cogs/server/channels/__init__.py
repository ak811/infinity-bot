# cogs/server/channels/__init__.py
from .cog import setup as setup_channels
from .archive_cog import setup as setup_archiver

async def setup(bot):
    await setup_channels(bot)
    await setup_archiver(bot)
