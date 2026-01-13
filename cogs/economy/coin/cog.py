# cogs/economy/coin/cog.py
from __future__ import annotations

import asyncio
import discord
from discord.ext import commands

from .service import get_total_coins, update_coins
from cogs.economy._shared import is_confirmation_enabled
from configs.helper import send_as_webhook
from utils.utils import log_coin_transaction  # keep existing logger utility

class CoinsCog(commands.Cog):
    """
    Coins-related commands:
      • !coins [@user] — show total coins
      • !send_coins @member <amount> — transfer with 5% fee (min 1), optional receiver approval
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---------- !coins ----------
    @commands.command(name="coins")
    async def coins(self, ctx: commands.Context, user: discord.Member | None = None):
        user = user or ctx.author
        if user != ctx.author and not ctx.message.mentions:
            await ctx.send("🙅 Please use a user mention (e.g. @username), not just a user ID.")
            return

        total = get_total_coins(str(user.id))
        await send_as_webhook(ctx, "coins", content=f"📊 **Total Coins for {user.mention}:** {total} 🪙")

    # ---------- !send_coins ----------
    @commands.command(name="send_coins")
    async def send_coins(self, ctx: commands.Context, member: discord.Member | None = None, coins: int | None = None):
        """Send coins to another member with a 5% fee (min 1)."""

        # Help embed if no args
        if member is None or coins is None:
            embed = discord.Embed(
                title="📘 Send Coins — Help",
                description="Transfer coins to another member (5% fee, min 1 🪙).",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="Usage", value="`!send_coins @member <amount>`", inline=False)
            embed.add_field(name="Example", value="`!send_coins @Alice 50`", inline=False)
            embed.add_field(name="Notes", value="• Must **mention** with `@`\n• Cannot send to yourself", inline=False)
            await send_as_webhook(ctx, "send_coins", embed=embed)
            return

        # Require a true mention
        if not ctx.message.mentions or ctx.message.mentions[0].id != member.id:
            embed = discord.Embed(
                title="🙅 Invalid Recipient",
                description="You must **mention** the recipient with `@`.",
                color=discord.Color.red(),
            )
            embed.add_field(name="Correct", value="`!send_coins @User 50`", inline=True)
            embed.add_field(name="Not allowed", value="IDs / usernames without tag", inline=True)
            await send_as_webhook(ctx, "send_coins", embed=embed)
            return

        if ctx.author == member:
            await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                description="🙅 You cannot send coins to yourself!",
                color=discord.Color.red()
            ))
            return

        if coins <= 0:
            await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                description="🙅 The amount must be greater than 0!",
                color=discord.Color.red()
            ))
            return

        fee = max(1, int(coins * 0.05))
        total_cost = coins + fee
        sender_total = get_total_coins(ctx.author.id)

        if total_cost > sender_total:
            await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                description=f"🙅 You need 🪙 {total_cost} to send 🪙 {coins} (fee: 🪙 {fee}).",
                color=discord.Color.red()
            ))
            return

        # Ask sender to confirm
        embed = discord.Embed(
            title="Confirm Transaction",
            description=(
                f"❗ You are about to send 🪙 {coins} to {member.mention} "
                f"(fee: 🪙 {fee}).\n\nType `yes` to confirm or `cancel` to abort."
            ),
            color=discord.Color.orange()
        )
        await send_as_webhook(ctx, "send_coins", embed=embed)

        def confirm_check(m: discord.Message):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "cancel"]

        try:
            user_input = await self.bot.wait_for("message", timeout=30.0, check=confirm_check)
        except asyncio.TimeoutError:
            await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                description="⌛ Sender confirmation timed out. Transaction cancelled.",
                color=discord.Color.red()
            ))
            return

        if user_input.content.lower() != "yes":
            await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                description="🙅 Transaction cancelled.",
                color=discord.Color.red()
            ))
            return

        if update_coins(ctx.author.id, -total_cost, "send") is False:
            await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                description="🙅 Transaction failed: insufficient coins.",
                color=discord.Color.red()
            ))
            return

        # Receiver confirmation if enabled
        if is_confirmation_enabled(member.id):
            embed = discord.Embed(
                title="Awaiting Approval",
                description=(
                    f"⏳ {ctx.author.mention} wants to send **🪙 {coins}** to {member.mention} "
                    f"(fee: 🪙 {fee}).\n\n{member.mention}, type `!approve` or `!decline` within 1 minute."
                ),
                color=discord.Color.orange()
            )
            await send_as_webhook(ctx, "send_coins", embed=embed)

            def receiver_check(m: discord.Message):
                return m.author == member and m.channel == ctx.channel and m.content.lower() in ["!approve", "!decline"]

            try:
                response = await self.bot.wait_for("message", timeout=60.0, check=receiver_check)
            except asyncio.TimeoutError:
                update_coins(ctx.author.id, total_cost, "refund")
                await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                    description=f"⌛ {member.mention} did not respond. Transaction cancelled and refunded.",
                    color=discord.Color.red()
                ))
                await log_coin_transaction(ctx, ctx.author, member, coins, "timeout", fee)
                return

            if response.content.lower() == "!approve":
                update_coins(member.id, coins, "receive")
                await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                    description=f"✅ Transaction approved! {ctx.author.mention} sent 🪙 {coins} to {member.mention}.",
                    color=discord.Color.green()
                ))
                await log_coin_transaction(ctx, ctx.author, member, coins, "approved", fee)
            else:
                update_coins(ctx.author.id, total_cost, "refund")
                await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                    description=f"🙅 Declined. 🪙 {total_cost} refunded to {ctx.author.mention}.",
                    color=discord.Color.red()
                ))
                await log_coin_transaction(ctx, ctx.author, member, coins, "declined", fee)
        else:
            update_coins(member.id, coins, "receive")
            await send_as_webhook(ctx, "send_coins", embed=discord.Embed(
                description=f"✅ {ctx.author.mention} sent 🪙 {coins} to {member.mention}.",
                color=discord.Color.green()
            ))
            await log_coin_transaction(ctx, ctx.author, member, coins, "auto", fee)

async def setup(bot: commands.Bot):
    await bot.add_cog(CoinsCog(bot))
