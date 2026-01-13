# cogs/shop/__init__.py
# Extension entry. Registers cogs and persistent views; updates pinned shop messages.

from __future__ import annotations

import discord
from discord.ext import commands

from .menu import ShopMenuCog
from .custom_roles import RoleIcon, CustomRolesShopView
from .subscription import SubscriptionShopView, build_subscription_shop
from .collectibles import CollectiblesShopView, build_collectibles_shop
from .exchange import CurrencyExchangeShopView, build_currency_exchange_shop
from .helpers import update_shop_message
from configs.config_channels import SHOP_CHANNEL_ID


async def _setup_all_shop_messages(bot: commands.Bot):
    embed, view = build_subscription_shop()
    await update_shop_message(bot, SHOP_CHANNEL_ID, "subscription_shop", embed, view)

    embed, view = build_collectibles_shop()
    await update_shop_message(bot, SHOP_CHANNEL_ID, "collectibles_shop", embed, view)

    embed, view = build_currency_exchange_shop()
    await update_shop_message(bot, SHOP_CHANNEL_ID, "currency_exchange_shop", embed, view)

    # Custom roles shop
    from .custom_roles import build_custom_roles_shop
    embed, view = build_custom_roles_shop()
    await update_shop_message(bot, SHOP_CHANNEL_ID, "custom_roles_shop", embed, view)


class _Bootstrap(commands.Cog):
    """Internal bootstrapper: registers persistent views & refreshes pinned messages once on_ready."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._did_ready = False
        # Register persistent views immediately
        bot.add_view(SubscriptionShopView())
        bot.add_view(CollectiblesShopView())
        bot.add_view(CurrencyExchangeShopView())
        bot.add_view(CustomRolesShopView())

    @commands.Cog.listener()
    async def on_ready(self):
        if self._did_ready:
            return
        self._did_ready = True
        try:
            await _setup_all_shop_messages(self.bot)
        except Exception as e:
            print(f"[cogs.shop] Failed to set up shop messages: {e}")


async def setup(bot: commands.Bot):
    # Visible cogs
    await bot.add_cog(ShopMenuCog(bot))
    await bot.add_cog(RoleIcon(bot))

    # Bootstrapper
    await bot.add_cog(_Bootstrap(bot))