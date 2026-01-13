# cogs/economy/dollar/cog.py
from __future__ import annotations

import discord
from discord.ext import commands
from .service import get_total_dollars
from configs.helper import send_as_webhook

class DollarsCog(commands.Cog):
    """
    !dollars [@user] — Show total wallet value (USD) with a per-currency breakdown.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="dollars")
    async def dollars(self, ctx: commands.Context, member: discord.Member | None = None):
        # Default to self; if target is someone else, require an actual mention
        member = member or ctx.author
        if member != ctx.author and not ctx.message.mentions:
            await ctx.send("🙅 Please use a user mention (e.g. @username), not just a user ID.")
            return

        usd = get_total_dollars(member.id, return_breakdown=True)
        embed = discord.Embed(
            title=f"💵 {member.display_name}'s Wallet (USD)",
            color=discord.Color.green()
        )
        embed.add_field(name="🪙 Coins (USD)",    value=f"${usd['coins']:.2f}", inline=True)
        embed.add_field(name="🔮 Orbs (USD)",     value=f"${usd['orbs']:.2f}", inline=True)
        embed.add_field(name="⭐ Stars (USD)",     value=f"${usd['stars']:.2f}", inline=True)
        embed.add_field(name="💎 Diamonds (USD)", value=f"${usd['diamonds']:.2f}", inline=True)
        embed.add_field(name="💰 Total", value=f"**${usd['total']:,.2f}**", inline=False)

        await send_as_webhook(ctx, "dollars", embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(DollarsCog(bot))
