from __future__ import annotations

import asyncio
from typing import Optional

import aiohttp
import discord
from discord.ext import commands, tasks

from configs.helper import send_as_webhook
BITCOIN_CHANNEL_ID = 1445105788329791558

COINBASE_API_URL = "https://api.coinbase.com/v2/prices/BTC-USD/spot"


class BitcoinCog(commands.Cog):
    """Bitcoin price feed: periodic posts and a manual command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session: Optional[aiohttp.ClientSession] = None

        print("[BitcoinCog] Initializing cog")
        try:
            self.price_loop.start()
            print("[BitcoinCog] price_loop started")
        except RuntimeError as e:
            print(f"[BitcoinCog] Failed to start price_loop: {e}")

    def cog_unload(self):
        print("[BitcoinCog] Unloading cog, stopping loop and closing session")
        if self.price_loop.is_running():
            self.price_loop.cancel()
            print("[BitcoinCog] price_loop cancelled")

        if self.session and not self.session.closed:
            asyncio.create_task(self.session.close())
            print("[BitcoinCog] aiohttp session close scheduled")

    async def get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            print("[BitcoinCog] Creating new aiohttp ClientSession")
            self.session = aiohttp.ClientSession()
        return self.session

    async def fetch_btc_price(self) -> Optional[float]:
        """Fetch BTC price in USD from Coinbase."""
        print("[BitcoinCog] Fetching BTC price from Coinbase API")
        try:
            session = await self.get_session()
            async with session.get(COINBASE_API_URL, timeout=10) as resp:
                print(f"[BitcoinCog] HTTP status: {resp.status}")
                if resp.status != 200:
                    print("[BitcoinCog] Non 200 response from Coinbase, returning None")
                    return None
                data = await resp.json()
                # Coinbase returns: {"data": {"base": "BTC", "currency": "USD", "amount": "12345.67"}}
                amount_str = data["data"]["amount"]
                price = float(amount_str)
                print(f"[BitcoinCog] Parsed BTC price from Coinbase: {price}")
                return price
        except Exception as e:
            print(f"[BitcoinCog] Error while fetching BTC price from Coinbase: {e}")
            return None

    def format_message(self, price: float) -> str:
        """Format the message for sending."""
        return f"**1 bitcoin** is worth **${price:,.2f} USD.**"

    @tasks.loop(minutes=10)
    async def price_loop(self):
        """Background loop that posts the BTC price every 5 minutes."""
        print("[BitcoinCog] price_loop tick")

        channel = self.bot.get_channel(BITCOIN_CHANNEL_ID)
        if channel is None:
            print(f"[BitcoinCog] Channel with id {BITCOIN_CHANNEL_ID} not found or not cached")
            return

        print(f"[BitcoinCog] Using channel: {channel} (id={channel.id})")

        price = await self.fetch_btc_price()
        if price is None:
            print("[BitcoinCog] BTC price is None, skipping send")
            return

        content = self.format_message(price)

        try:
            await send_as_webhook(channel, "bitcoin", content=content)
            print(f"[BitcoinCog] Replied to command with BTC price: {content}")
        except Exception as e:
            print(f"[BitcoinCog] Failed to send via webhook, falling back to normal send: {e}")
            await channel.reply(content)
            print("[BitcoinCog] Fallback reply sent")

    @price_loop.before_loop
    async def before_price_loop(self):
        print("[BitcoinCog] Waiting for bot to be ready before starting price_loop")
        await self.bot.wait_until_ready()
        print("[BitcoinCog] Bot is ready, price_loop will start now")

    @commands.command(name="bitcoin", aliases=["btc"])
    async def bitcoin_command(self, ctx: commands.Context):
        """Show the current BTC price on demand."""
        print(f"[BitcoinCog] bitcoin_command called by {ctx.author} in {ctx.channel}")
        async with ctx.typing():
            price = await self.fetch_btc_price()
            if price is None:
                print("[BitcoinCog] Command fetch returned None, replying with error")
                await ctx.reply("Could not fetch BTC price right now. Try again later.")
                return

            content = self.format_message(price)
            try:
                await send_as_webhook(ctx, "bitcoin", content=content)
                print(f"[BitcoinCog] Replied to command with BTC price: {content}")
            except Exception as e:
                print(f"[BitcoinCog] Failed to send via webhook, falling back to normal send: {e}")
                await ctx.reply(content)
                print("[BitcoinCog] Fallback reply sent")


async def setup(bot: commands.Bot):
    print("[BitcoinCog] setup() called, adding cog")
    await bot.add_cog(BitcoinCog(bot))
    print("[BitcoinCog] Cog added")
