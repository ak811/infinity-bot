from __future__ import annotations

import discord
from discord.ext import commands
from configs.helper import send_as_webhook
from cogs.fun._shared import safe_random_from_json, FORTUNE_PATH

class FortuneCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="fortune", help="Get your fortune cookie message!")
    async def fortune(self, ctx: commands.Context):
        fallback = [
            "Good fortune will smile upon you in the coming days.",
            "Trust your instincts—they will guide you to success."
        ]
        txt = safe_random_from_json(FORTUNE_PATH, fallback, "fortune")
        embed = discord.Embed(title="🥠 Your Fortune Cookie", description=txt, color=discord.Color.blurple())
        await send_as_webhook(ctx, "fortune", embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(FortuneCog(bot))
