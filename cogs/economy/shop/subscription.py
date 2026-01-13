# cogs/shop/subscription.py
from __future__ import annotations

import discord
from .helpers import generate_shop_embed
from utils.utils_json import load_json, save_json
from configs.config_files import USER_DIAMONDS_FILE
from configs.config_channels import LOGS_CHANNEL_ID


class SubscriptionConfirmView(discord.ui.View):
    def __init__(self, cost: int, item_name: str):
        super().__init__(timeout=15)
        self.cost = cost
        self.item_name = item_name

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = str(interaction.user.id)
        diamond_data = load_json(USER_DIAMONDS_FILE)
        user_diamonds = diamond_data.get(user_id, 0)
        if user_diamonds < self.cost:
            await interaction.response.edit_message(
                content=f"🙅 You don’t have enough 💎 Diamonds for {self.item_name}!", view=None
            )
            return
        diamond_data[user_id] = user_diamonds - self.cost
        save_json(USER_DIAMONDS_FILE, diamond_data)
        await interaction.response.edit_message(
            content=f"✅ You purchased **{self.item_name}** for {self.cost}💎!", view=None
        )
        staff_channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
        if staff_channel:
            embed = discord.Embed(title="🛒 Subscription Purchase", color=discord.Color.orange())
            embed.add_field(name="User", value=interaction.user.mention, inline=True)
            embed.add_field(name="Item", value=self.item_name, inline=True)
            embed.add_field(name="Cost", value=f"{self.cost} 💎", inline=True)
            embed.set_footer(text=f"User ID: {user_id}")
            await staff_channel.send(embed=embed)

    @discord.ui.button(label="🙅 Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❎ Purchase cancelled.", view=None)


class SubscriptionShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Steam Gift Card (150💎)", style=discord.ButtonStyle.green,
                       custom_id="buy_steam_gift_card", row=0)
    async def buy_steam_gift_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Are you sure you want to purchase **Steam Gift Card** for **150💎**?",
            view=SubscriptionConfirmView(150, "Steam Gift Card"), ephemeral=True
        )

    @discord.ui.button(label="Google Play Gift Card (300💎)", style=discord.ButtonStyle.green,
                       custom_id="buy_google_play_gift_card", row=0)
    async def buy_google_play_gift_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Are you sure you want to purchase **Google Play Gift Card** for **300💎**?",
            view=SubscriptionConfirmView(300, "Google Play Gift Card"), ephemeral=True
        )

    @discord.ui.button(label="Amazon Gift Card (300💎)", style=discord.ButtonStyle.green,
                       custom_id="buy_amazon_gift_card", row=0)
    async def buy_amazon_gift_card(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Are you sure you want to purchase **Amazon Gift Card** for **300💎**?",
            view=SubscriptionConfirmView(300, "Amazon Gift Card"), ephemeral=True
        )

    @discord.ui.button(label="Spotify (300💎)", style=discord.ButtonStyle.blurple,
                       custom_id="buy_spotify_subscription", row=1)
    async def buy_spotify_subscription(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Are you sure you want to purchase **1 Month Spotify Subscription** for **300💎**?",
            view=SubscriptionConfirmView(300, "1 Month Spotify Subscription"), ephemeral=True
        )

    @discord.ui.button(label="Netflix (450💎)", style=discord.ButtonStyle.blurple,
                       custom_id="buy_netflix_subscription", row=1)
    async def buy_netflix_subscription(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Are you sure you want to purchase **1 Month Netflix Subscription** for **450💎**?",
            view=SubscriptionConfirmView(450, "1 Month Netflix Subscription"), ephemeral=True
        )

    @discord.ui.button(label="Nitro Classic (100💎)", style=discord.ButtonStyle.red,
                       custom_id="buy_nitro_classic", row=2)
    async def buy_nitro_classic(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Are you sure you want to purchase **1 Month Nitro Classic Subscription** for **100💎**?",
            view=SubscriptionConfirmView(100, "1 Month Nitro Classic Subscription"), ephemeral=True
        )

    @discord.ui.button(label="Nitro Premium (300💎)", style=discord.ButtonStyle.red,
                       custom_id="buy_nitro_premium", row=2)
    async def buy_nitro_premium(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Are you sure you want to purchase **1 Month Nitro Premium Subscription** for **300💎**?",
            view=SubscriptionConfirmView(300, "1 Month Nitro Premium Subscription"), ephemeral=True
        )


def build_subscription_shop():
    description = (
        "**🎁 Gift Cards:**\n"
        "• 🟦 Steam Gift Card - 150 💎\n"
        "• 📱 Google Play Gift Card - 300 💎\n"
        "• 📦 Amazon Gift Card - 300 💎\n\n"
        "**📅 1 Month Subscriptions:**\n"
        "• 🎵 Spotify - 300 💎\n"
        "• 🎬 Netflix - 450 💎\n\n"
        "**💬 Discord Nitro:**\n"
        "• 🟣 Nitro Classic - 100 💎\n"
        "• 🔥 Nitro Premium - 300 💎"
    )
    embed = generate_shop_embed(
        title="💳 Subscription Shop",
        description=description,
        footer="Spend your diamonds on premium digital goods!",
        color=discord.Color.purple()
    )
    view = SubscriptionShopView()
    return embed, view