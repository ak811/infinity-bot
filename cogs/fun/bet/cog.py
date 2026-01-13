from __future__ import annotations

import asyncio, random
import discord
from discord.ext import commands

from cogs.economy.coin.service import update_coins, get_total_coins
from configs.helper import send_as_webhook

class BetCog(commands.Cog):
    """Challenge another user to a coin bet. Winner takes the pot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="bet")
    async def bet(self, ctx: commands.Context, member: discord.Member | None = None, coins: int | None = None):
        # Help embed if no args
        if member is None or coins is None:
            embed = discord.Embed(
                title="📘 Bet — Help",
                description="Challenge another user to a coin bet. Both must accept. Winner takes the pot (2×).",
                color=discord.Color.gold(),
            )
            embed.add_field(name="Usage", value="`!bet @member <amount>`", inline=False)
            embed.add_field(name="Example", value="`!bet @Bob 100`", inline=False)
            embed.add_field(name="Rules", value="• Both must have enough coins\n• Winner chosen randomly\n• Pot = `amount × 2`", inline=False)
            embed.add_field(name="Note", value="You must **mention** your opponent with `@`.", inline=False)
            await send_as_webhook(ctx, "bet", embed=embed)
            return

        # Require a true mention
        if not ctx.message.mentions or ctx.message.mentions[0].id != member.id:
            embed = discord.Embed(
                title="🙅 Invalid Opponent",
                description="You must **mention** your opponent.",
                color=discord.Color.red(),
            )
            embed.add_field(name="Correct", value="`!bet @User 100`", inline=True)
            embed.add_field(name="Not allowed", value="IDs / usernames without tag", inline=True)
            await send_as_webhook(ctx, "bet", embed=embed)
            return

        if ctx.author == member:
            await send_as_webhook(ctx, "bet", embed=discord.Embed(
                description="🙅 You cannot bet against yourself!",
                color=discord.Color.red()
            ))
            return

        if coins <= 0:
            await send_as_webhook(ctx, "bet", embed=discord.Embed(
                description="🙅 The bet amount must be greater than 0!",
                color=discord.Color.red()
            ))
            return

        sender_total = get_total_coins(ctx.author.id)
        receiver_total = get_total_coins(member.id)
        if coins > sender_total:
            await send_as_webhook(ctx, "bet", embed=discord.Embed(
                description=f"🙅 {ctx.author.mention}, you do not have enough coins.",
                color=discord.Color.red()
            ))
            return
        if coins > receiver_total:
            await send_as_webhook(ctx, "bet", embed=discord.Embed(
                description=f"🙅 {member.mention}, you do not have enough coins.",
                color=discord.Color.red()
            ))
            return

        # Ask opponent to accept
        message = await send_as_webhook(ctx, "bet", embed=discord.Embed(
            description=(f"🎲 {ctx.author.mention} challenged {member.mention} to a bet of 🪙 {coins}!\n\n"
                         f"Waiting for {member.mention} to respond with `accept` or `decline`..."),
            color=discord.Color.orange()
        ))

        def check(m: discord.Message):
            return m.author == member and m.channel == ctx.channel and m.content.lower() in ["accept", "decline"]

        try:
            reply = await self.bot.wait_for("message", check=check, timeout=60.0)
            if reply.content.lower() == "decline":
                await message.edit(embed=discord.Embed(
                    description=f"🙅 {member.mention} declined the bet.",
                    color=discord.Color.red()
                ))
                return
        except asyncio.TimeoutError:
            await message.edit(embed=discord.Embed(
                description=f"⌛ Bet request timed out. {member.mention} did not respond.",
                color=discord.Color.red()
            ))
            return

        await message.edit(embed=discord.Embed(
            description=f"🎲 {ctx.author.mention} and {member.mention} accepted the bet of 🪙 {coins} each!\nRolling the dice... 🎲",
            color=discord.Color.orange()
        ))

        result_sender = update_coins(ctx.author.id, -coins, "bet")
        result_receiver = update_coins(member.id, -coins, "bet")
        if result_sender is False or result_receiver is False:
            await send_as_webhook(ctx, "bet", embed=discord.Embed(
                description="🙅 Error processing the bet due to insufficient coins.",
                color=discord.Color.red()
            ))
            return

        winner = random.choice([ctx.author, member])
        pot = coins * 2
        update_coins(winner.id, pot, "bet winner")

        sender_coins = get_total_coins(ctx.author.id)
        receiver_coins = get_total_coins(member.id)

        await asyncio.sleep(2)
        result_embed = discord.Embed(
            title="🎲 Bet Result",
            description=f"🏆 **Winner:** {winner.mention}!\nThey won the pot of 🪙 {pot}.",
            color=discord.Color.green()
        )
        result_embed.add_field(name=ctx.author.display_name, value=f"{sender_coins} 🪙", inline=True)
        result_embed.add_field(name=member.display_name, value=f"{receiver_coins} 🪙", inline=True)

        await message.edit(embed=result_embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(BetCog(bot))
