from __future__ import annotations

import discord
from discord.ext import commands
from configs.helper import send_as_webhook
from cogs.fun._shared import safe_random_from_json, COMPLIMENTS_PATH

class ComplimentCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="compliment")
    async def compliment(self, ctx: commands.Context, member: commands.MemberConverter | None = None):
        fallback = [
            "You’re a knockout!",
            "Is your name Wi-Fi? Because I’m feeling a strong connection."
        ]
        text = safe_random_from_json(COMPLIMENTS_PATH, fallback, "compliment")
        target = member.mention if member else ctx.author.mention
        embed = discord.Embed(title="🌟 Compliment", description=f"{target}, {text}", color=discord.Color.gold())
        await send_as_webhook(ctx, "compliment", embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ComplimentCog(bot))
