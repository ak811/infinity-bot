# cogs/server/emojis/__init__.py
# from .cog import setup  # old
async def setup(bot):      # new: proxy to avoid early imports
    from .cog import setup as _setup
    await _setup(bot)
