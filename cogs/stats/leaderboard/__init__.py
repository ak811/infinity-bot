# cogs/leaderboard/__init__.py
import importlib
from discord.ext import commands

async def setup(bot: commands.Bot):
    # Load the dropdown menu (was previously re-exported)
    menu = importlib.import_module("cogs.stats.leaderboard.menu")
    await menu.setup(bot)

    # Load & start the auto-embed updater
    updater = importlib.import_module("cogs.stats.leaderboard.embed_update")
    await updater.setup(bot)
