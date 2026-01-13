# cogs/economy/orb/cog.py
from __future__ import annotations

import discord
from discord.ext import commands
from .service import get_total_orbs
from configs.helper import send_as_webhook

class OrbsCog(commands.Cog):
    """!orbs — show total orbs for a user (or yourself)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="orbs")
    async def orbs(self, ctx: commands.Context, user: discord.Member | None = None):
        user = user or ctx.author
        if user != ctx.author and not ctx.message.mentions:
            await ctx.send("🙅 Please use a user mention (e.g. @username), not just a user ID.")
            return

        total = get_total_orbs(str(user.id))
        await send_as_webhook(ctx, "orbs", content=f"📊 **Total Orbs for {user.mention}:** {total} 🔮")

async def setup(bot: commands.Bot):
    await bot.add_cog(OrbsCog(bot))
