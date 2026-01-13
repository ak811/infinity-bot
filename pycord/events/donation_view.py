# pycord/events/donation_view.py

import discord
from configs.config_logging import logging
from cogs.economy.coin.service import update_coins
from cogs.economy.orb.service import update_orbs
from cogs.economy.star.service import update_stars
from cogs.economy.diamond.service import update_diamonds

from configs.helper import send_as_webhook

# track donation logs: (host_id, event_name) → list of (donor_id, type, amount)
donation_logs: dict[tuple[int, str], list[tuple[int, str, int]]] = {}

__all__ = [
    "DonationView",
    "DonateButton",
    "DonateOrbButton",
    "DonateDiamondButton",
    "DonateStarButton",
    "send_donation_message",
]

# ---- Helper -------------------------------------------------

def _simple_embed(description: str, *, color: int = 0x5865F2) -> discord.Embed:
    """Create a minimal embed with only a description."""
    return discord.Embed(description=description, color=color)

# Colors
COLOR_COIN = 0xF1C40F
COLOR_ORB = 0x9B59B6
COLOR_DIAMOND = 0xB9F2FF
COLOR_WARN = 0xE67E22
COLOR_ERR = 0xE74C3C
COLOR_INFO = 0x5865F2

# ---- View & Buttons -----------------------------------------

class DonationView(discord.ui.View):
    def __init__(self, host_id: int, event_name: str):
        super().__init__(timeout=None)
        # Row 0: 🪙 & 🔮
        self.add_item(DonateButton(host_id, event_name))       # 🪙
        self.add_item(DonateOrbButton(host_id, event_name))    # 🔮

        # Row 1: ⭐ & 💎
        self.add_item(DonateStarButton(host_id, event_name))   # ⭐
        self.add_item(DonateDiamondButton(host_id, event_name))  # 💎

class DonateButton(discord.ui.Button):
    def __init__(self, host_id: int, event_name: str):
        super().__init__(
            label="Donate 1 🪙",
            style=discord.ButtonStyle.success,
            custom_id="donate_coin",
            row=0,
        )
        self.host_id = host_id
        self.event_name = event_name

    async def callback(self, interaction: discord.Interaction):
        donor = interaction.user
        if donor.id == self.host_id:
            await interaction.response.send_message(
                embed=_simple_embed("⚠️ You’re the host! You can’t donate to yourself 🙂", color=COLOR_WARN),
                ephemeral=True
            )
            return

        # Attempt to deduct coin
        success = update_coins(donor.id, -1)
        if not success:
            await interaction.response.send_message(
                embed=_simple_embed("🙅 You don’t have enough coins!", color=COLOR_ERR),
                ephemeral=True
            )
            return

        # Add coin to host
        update_coins(self.host_id, +1)

        # record in donation_logs
        donation_logs.setdefault((self.host_id, self.event_name), []).append((donor.id, "coin", 1))

        await interaction.response.defer()

        await send_as_webhook(
            interaction.channel,
            "event",
            embed=_simple_embed(
                f"🪙 {donor.mention} donated **1 coin** to <@{self.host_id}> for hosting **{self.event_name}**!",
                color=COLOR_COIN
            )
        )


class DonateOrbButton(discord.ui.Button):
    def __init__(self, host_id: int, event_name: str):
        super().__init__(
            label="Donate 1 🔮",
            style=discord.ButtonStyle.success,
            custom_id="donate_orb",
            row=0, 
        )
        self.host_id = host_id
        self.event_name = event_name

    async def callback(self, interaction: discord.Interaction):
        donor = interaction.user
        if donor.id == self.host_id:
            await interaction.response.send_message(
                embed=_simple_embed("⚠️ You’re the host! You can’t donate to yourself 🙂", color=COLOR_WARN),
                ephemeral=True
            )
            return

        success = update_orbs(donor.id, -1)
        if not success:
            await interaction.response.send_message(
                embed=_simple_embed("🙅 You don’t have enough orbs!", color=COLOR_ERR),
                ephemeral=True
            )
            return

        update_orbs(self.host_id, +1)

        donation_logs.setdefault((self.host_id, self.event_name), []).append((donor.id, "orb", 1))

        await interaction.response.defer()

        await send_as_webhook(
            interaction.channel,
            "event",
            embed=_simple_embed(
                f"🔮 {donor.mention} donated **1 orb** to <@{self.host_id}> for hosting **{self.event_name}**!",
                color=COLOR_ORB
            )
        )

class DonateStarButton(discord.ui.Button):
    def __init__(self, host_id: int, event_name: str):
        super().__init__(
            label="Donate 1 ⭐",
            style=discord.ButtonStyle.primary,
            custom_id="donate_star",
            row=1
        )
        self.host_id = host_id
        self.event_name = event_name

    async def callback(self, interaction: discord.Interaction):
        donor = interaction.user
        if donor.id == self.host_id:
            await interaction.response.send_message(
                embed=_simple_embed("⚠️ You’re the host! You can’t donate to yourself 🙂", color=COLOR_WARN),
                ephemeral=True
            )
            return

        success = update_stars(donor.id, -1)
        if not success:
            await interaction.response.send_message(
                embed=_simple_embed("🙅 You don’t have enough stars!", color=COLOR_ERR),
                ephemeral=True
            )
            return

        update_stars(self.host_id, +1)

        donation_logs.setdefault((self.host_id, self.event_name), []).append((donor.id, "star", 1))

        await interaction.response.defer()

        await send_as_webhook(
            interaction.channel,
            "event",
            embed=_simple_embed(
                f"⭐ {donor.mention} donated **1 star** to <@{self.host_id}> for hosting **{self.event_name}**!",
                color=0xF1C40F  # you can change to STAR_COLOR if defined
            )
        )

class DonateDiamondButton(discord.ui.Button):
    def __init__(self, host_id: int, event_name: str):
        super().__init__(
            label="Donate 1 💎",
            style=discord.ButtonStyle.primary,
            custom_id="donate_diamond",
            row=1,
        )
        self.host_id = host_id
        self.event_name = event_name

    async def callback(self, interaction: discord.Interaction):
        donor = interaction.user
        if donor.id == self.host_id:
            await interaction.response.send_message(
                embed=_simple_embed("⚠️ You’re the host! You can’t donate to yourself 🙂", color=COLOR_WARN),
                ephemeral=True
            )
            return

        success = update_diamonds(donor.id, -1)
        if not success:
            await interaction.response.send_message(
                embed=_simple_embed("🙅 You don’t have enough diamonds!", color=COLOR_ERR),
                ephemeral=True
            )
            return

        update_diamonds(self.host_id, +1)

        # ✅ Only log after a successful deduction (fix #5)
        donation_logs.setdefault((self.host_id, self.event_name), []).append((donor.id, "diamond", 1))

        await interaction.response.defer()

        await send_as_webhook(
            interaction.channel,
            "event",
            embed=_simple_embed(
                f"💎 {donor.mention} donated **1 diamond** to <@{self.host_id}> for hosting **{self.event_name}**!",
                color=COLOR_DIAMOND
            )
        )


# ---- Public API ---------------------------------------------

async def send_donation_message(channel, host_id: int, event_name: str):
    """
    Send a donation prompt in the channel using the 'event' persona (as an embed).
    """
    try:
        view = DonationView(host_id, event_name)
        embed = discord.Embed(
            title=f"Spread Some Love 💝",
            description=(
                f"💝 Want to appreciate the host of **{event_name}**?\n"
            ),
            color=COLOR_INFO
        )
        await send_as_webhook(
            channel,
            "event",
            embed=embed,
            view=view
        )
        logging.info(f"[Donate] Sent donation message for {event_name}")
    except Exception:
        logging.exception(f"[Donate] Failed to send donation message for {event_name}")
