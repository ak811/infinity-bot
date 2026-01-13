# cogs/shop/collectibles.py
from __future__ import annotations

import discord
from .helpers import generate_shop_embed

from cogs.economy.orb.service import update_orbs, get_total_orbs

from configs.config_channels import LOGS_CHANNEL_ID


class SendRoseModal(discord.ui.Modal, title="Send a Rose"):
    target_user_id = discord.ui.TextInput(label="Enter the target user ID", placeholder="123456789012345678", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        cost = 1
        if get_total_orbs(user_id) < cost:
            await interaction.response.send_message("🙅 You don't have enough 🔮 orbs to send a rose!", ephemeral=True)
            return
        try:
            target_id = int(self.target_user_id.value.strip())
        except ValueError:
            await interaction.response.send_message("🙅 Invalid user ID.", ephemeral=True)
            return
        target_user = interaction.client.get_user(target_id) or await interaction.client.fetch_user(target_id)
        try:
            await target_user.send("💐 You have received a rose 🌹 from someone special!")
        except Exception:
            await interaction.response.send_message("🙅 Failed to send a message to the target user.", ephemeral=True)
            return
        update_orbs(user_id, -cost, "rose")
        channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🌹 A Rose Has Been Sent!", color=discord.Color.red())
            embed.add_field(name="From", value=interaction.user.mention, inline=True)
            embed.add_field(name="To", value=f"<@{target_id}>", inline=True)
            embed.set_footer(text="Someone just made someone's day a little brighter!")
            await channel.send(embed=embed)
        await interaction.response.send_message("✅ Your rose has been sent anonymously!", ephemeral=True)


class CollectiblesShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Buy Rose (1🔮)", style=discord.ButtonStyle.success, custom_id="buy_rose")
    async def buy_rose(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SendRoseModal())

    @discord.ui.button(label="Coming Soon (1🔮)", style=discord.ButtonStyle.secondary, custom_id="buy_car")
    async def buy_car(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚗 Feature Coming Soon!", ephemeral=True)

    @discord.ui.button(label="Coming Soon (1🔮)", style=discord.ButtonStyle.secondary, custom_id="buy_fireworks")
    async def buy_fireworks(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🎆 Feature Coming Soon!", ephemeral=True)


def build_collectibles_shop():
    description = (
        "Be creative with your purchases!\n\n"
        "💐 **Send a Rose** - 1 🔮\n"
        "🏎️ **Coming soon** - 1 🔮\n"
        "🎇 **Coming soon** - 1 🔮\n\n"
        "For example, sending a rose will deliver an anonymous love message."
    )
    embed = generate_shop_embed(
        title="🌟 Collectibles Shop",
        description=description,
        footer="Collect and celebrate your favorite moments!",
        color=discord.Color.dark_magenta()
    )
    view = CollectiblesShopView()
    return embed, view