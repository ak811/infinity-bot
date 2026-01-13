# cogs/economy/bank/cog.py
from __future__ import annotations

import discord
from discord.ext import commands

from cogs.economy.coin.service import get_total_coins
from cogs.economy.orb.service import get_total_orbs
from cogs.economy.star.service import get_total_stars
from cogs.economy.diamond.service import get_total_diamonds
from configs.helper import send_as_webhook
from configs.config_general import BOT_USER_ID

class BankCog(commands.Cog):
    """!bank — Café Treasury summary with caps and USD estimates."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="bank", aliases=["b"])
    async def bank(self, ctx: commands.Context):
        async with ctx.typing():
            COIN_CAP, ORB_CAP, STAR_CAP, DIAMOND_CAP = 500_000, 30_000, 2_000, 2_000
            BAR_LENGTH = 10

            DIAMOND_USD = 5 / 150
            STAR_USD = DIAMOND_USD / 10
            ORB_USD  = DIAMOND_USD / 100
            COIN_USD = DIAMOND_USD / 1000

            def to_usd(coins=0, orbs=0, stars=0, diamonds=0):
                return coins*COIN_USD + orbs*ORB_USD + stars*STAR_USD + diamonds*DIAMOND_USD

            members = [m for m in ctx.guild.members if not m.bot]
            total_coins    = sum(get_total_coins(m.id) for m in members)
            total_orbs     = sum(get_total_orbs(m.id) for m in members)
            total_stars    = sum(get_total_stars(m.id) for m in members)
            total_diamonds = sum(get_total_diamonds(m.id) for m in members)

            coins_left    = max(0, COIN_CAP - total_coins)
            orbs_left     = max(0, ORB_CAP - total_orbs)
            diamonds_left = max(0, DIAMOND_CAP - total_diamonds)
            stars_left    = max(0, STAR_CAP - total_stars)

            bot_member = ctx.guild.get_member(BOT_USER_ID)
            IMAGE_PATH = "database/images/server_profile.png"
            IMAGE_NAME = "server_profile.png"
            avatar_url = bot_member.avatar.url if bot_member and bot_member.avatar else f"attachment://{IMAGE_NAME}"

            def bar(used, cap, length=BAR_LENGTH):
                ratio = min(1.0, used / cap) if cap else 0
                filled = int(ratio * length)
                return "▰"*filled + "▱"*(length - filled)

            embed = discord.Embed(title="🏦 Café Treasury", color=discord.Color.gold())
            embed.set_thumbnail(url=avatar_url)

            embed.add_field(
                name=f"🪙 {coins_left:,} Coins Left",
                value=f"{bar(total_coins, COIN_CAP)}\n{total_coins:,} coins in circulation **(${to_usd(coins=total_coins):.2f})**",
                inline=False
            )
            embed.add_field(
                name=f"🔮 {orbs_left:,} Orbs Left",
                value=f"{bar(total_orbs, ORB_CAP)}\n{total_orbs:,} orbs in circulation **(${to_usd(orbs=total_orbs):.2f})**",
                inline=False
            )
            embed.add_field(
                name=f"⭐ {stars_left:,} Stars Left",
                value=f"{bar(total_stars, STAR_CAP)}\n{total_stars:,} stars in circulation **(${to_usd(stars=total_stars):.2f})**",
                inline=False
            )
            embed.add_field(
                name=f"💎 {diamonds_left:,} Diamonds Left",
                value=f"{bar(total_diamonds, DIAMOND_CAP)}\n{total_diamonds:,} diamonds in circulation **(${to_usd(diamonds=total_diamonds):.2f})**",
                inline=False
            )

            total_usd = to_usd(total_coins, total_orbs, total_stars, total_diamonds)
            embed.set_footer(text=f"💵 Total dollars in circulation: ${total_usd:,.2f}")

            if bot_member and not bot_member.avatar:
                file = discord.File(IMAGE_PATH, filename=IMAGE_NAME)
                await send_as_webhook(ctx, "treasury", embed=embed, file=file)
            else:
                await send_as_webhook(ctx, "treasury", embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(BankCog(bot))
