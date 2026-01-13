from __future__ import annotations

import discord
from discord.ext import commands
from configs.helper import send_as_webhook
from cogs.fun._shared import safe_random_from_json, TOPICS_PATH

class TopicCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="topic", help="Get a random topic for discussion!")
    async def topic(self, ctx: commands.Context):
        fallback = [
            "If you could travel anywhere in the world, where would it be and why?",
            "What’s your favorite childhood memory?",
        ]
        txt = safe_random_from_json(TOPICS_PATH, fallback, "topic")
        embed = discord.Embed(title="💬 Conversation Starter", description=txt, color=discord.Color.blurple())
        await send_as_webhook(ctx, "topic", embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TopicCog(bot))
