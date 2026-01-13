# cogs/automatic_reactions/cog.py
from __future__ import annotations

import logging
import discord
from discord.ext import commands

from .mapping import REACTION_MAP, NICE, SLOTH_USER_ID

class AutomaticReactionsCog(commands.Cog):
    """Adds predefined emoji reactions in selected channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        # Ignore system messages
        if not isinstance(message.channel, discord.TextChannel):
            return
        # Optional: ignore bot authors; remove this if you *want* to react to bots too
        if message.author.bot:
            return

        channel_id = message.channel.id

        # Find matching group
        reactions: list[str] | None = None
        for channels, emojis in REACTION_MAP.items():
            if channel_id in channels:
                # copy so we don't mutate the template list
                reactions = list(emojis)
                break

        if not reactions:
            return

        # Special sloth case: NICE channels + specific author
        if channel_id in NICE and message.author.id == SLOTH_USER_ID:
            reactions.append('🦥')

        # Add reactions
        try:
            for emoji in reactions:
                await message.add_reaction(emoji)
        except discord.HTTPException as e:
            self.log.debug(f"[AutoReact] Failed to add reactions in #{message.channel.name}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(AutomaticReactionsCog(bot))
