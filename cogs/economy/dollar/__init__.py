# cogs/economy/dollar/__init__.py
from .cog import setup  # enables: await bot.load_extension("cogs.economy.dollar")
from .service import get_total_dollars  # optional convenience re-export
