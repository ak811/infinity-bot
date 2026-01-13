from __future__ import annotations

import discord
from discord.ext import commands

from .subscription import build_subscription_shop
from .collectibles import build_collectibles_shop
from .exchange import build_currency_exchange_shop
from .custom_roles import build_custom_roles_shop
from configs.helper import send_as_webhook


class ShopMenu(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.select = ShopSelect(ctx)
        self.add_item(self.select)


class ShopSelect(discord.ui.Select):
    def __init__(self, ctx):
        options = [
            discord.SelectOption(label="🌟 Collectibles Shop",     value="collectibles_shop"),
            discord.SelectOption(label="💳 Subscription Shop",     value="subscription_shop"),
            discord.SelectOption(label="💎 Currency Exchange Shop", value="currency_exchange_shop"),
            discord.SelectOption(label="🎨 Custom Roles Shop",     value="custom_roles_shop"),
        ]
        super().__init__(placeholder="Select a shop…", min_values=1, max_values=1, options=options)
        self.ctx = ctx
        self.author = ctx.author

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("This menu isn’t for you!", ephemeral=True)
        cmd = self.values[0]
        if cmd == "subscription_shop":
            embed, shop_view = build_subscription_shop()
        elif cmd == "currency_exchange_shop":
            embed, shop_view = build_currency_exchange_shop()
        elif cmd == "collectibles_shop":
            embed, shop_view = build_collectibles_shop()
        elif cmd == "custom_roles_shop":
            embed, shop_view = build_custom_roles_shop()
        else:
            return await interaction.response.send_message("Unknown shop selection.", ephemeral=True)
        shop_view.add_item(ShopSelect(self.ctx))
        await interaction.response.edit_message(embed=embed, view=shop_view)


class ShopMenuCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="shop", help="Pick any shop from the dropdown menu.")
    async def shop_menu(self, ctx: commands.Context):
        view = ShopMenu(ctx)
        embed = discord.Embed(
            title="🛒 Welcome to the Shop!",
            description="Choose a shop from the dropdown menu below.",
            color=discord.Color.green()
        )
        await send_as_webhook(ctx, "shop", embed=embed, view=view)

    @commands.command(name="refresh_shops", help="(Admin) Rebuild and update all shop messages.")
    @commands.has_guild_permissions(manage_guild=True)
    async def sudo_refresh_shops(self, ctx: commands.Context):
        # Import late to avoid circulars
        from . import _setup_all_shop_messages
        await _setup_all_shop_messages(self.bot)
        await ctx.reply("✅ Shop messages refreshed.")