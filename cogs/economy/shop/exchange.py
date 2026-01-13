# cogs/shop/exchange.py
from __future__ import annotations

import math
import discord
from .helpers import generate_shop_embed

from cogs.economy.coin.service import update_coins, get_total_coins
from cogs.economy.orb.service import update_orbs, get_total_orbs
from cogs.economy.star.service import update_stars, get_total_stars
from cogs.economy.diamond.service import update_diamonds, get_total_diamonds

from configs.config_channels import LOGS_CHANNEL_ID
from configs.config_general import AUTHORIZED_USER_ID
from configs.helper import send_as_webhook


class CurrencyExchangeShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="🪙 1000 → 💎 1", style=discord.ButtonStyle.success, custom_id="c_to_d", row=0))
        self.add_item(discord.ui.Button(label="💎 1 → 🪙 1000", style=discord.ButtonStyle.success, custom_id="d_to_c", row=0))
        self.add_item(discord.ui.Button(label="🪙 100 → ⭐ 1", style=discord.ButtonStyle.primary, custom_id="c_to_s", row=1))
        self.add_item(discord.ui.Button(label="⭐ 1 → 🪙 100", style=discord.ButtonStyle.primary, custom_id="s_to_c", row=1))
        self.add_item(discord.ui.Button(label="🪙 10 → 🔮 1", style=discord.ButtonStyle.danger, custom_id="c_to_o", row=2))
        self.add_item(discord.ui.Button(label="🔮 1 → 🪙 10", style=discord.ButtonStyle.danger, custom_id="o_to_c", row=2))
        self.add_item(discord.ui.Button(label="💵 $5 → 💎 150", style=discord.ButtonStyle.secondary, custom_id="usd_to_d", row=3))
        self.add_item(discord.ui.Button(label="💎 150 → 💵 $5", style=discord.ButtonStyle.secondary, custom_id="d_to_usd", row=3))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        custom_id = interaction.data.get("custom_id")
        if custom_id == "usd_to_d":
            guild = interaction.guild
            staff = guild.get_member(AUTHORIZED_USER_ID) if guild else None
            contact = f"{staff.mention} (**{staff.display_name}**)" if staff else f"<@{AUTHORIZED_USER_ID}>"
            await interaction.response.send_message(
                f"🛡️ For 💵 **$5** ⇄ 💎 **150** exchanges, please contact {contact}.", ephemeral=True
            )
            return False
        if custom_id == "d_to_usd":
            user_id = str(interaction.user.id)
            if get_total_diamonds(user_id) < 150:
                await interaction.response.send_message("🙅 You need at least 💎 150 to exchange for $5.", ephemeral=True)
                return False
            guild = interaction.guild
            staff = guild.get_member(AUTHORIZED_USER_ID) if guild else None
            contact = f"{staff.mention} (**{staff.display_name}**)" if staff else f"<@{AUTHORIZED_USER_ID}>"
            await interaction.response.send_message(
                f"🛡️ To exchange 💎 **150** for 💵 **$5**, please contact {contact}.", ephemeral=True
            )
            return False

        mapping = {
            "c_to_d": ("coins", "diamond", 1000, 1),
            "d_to_c": ("diamond", "coins", 1, 1000),
            "c_to_s": ("coins", "stars", 100, 1),
            "s_to_c": ("stars", "coins", 1, 100),
            "c_to_o": ("coins", "orbs", 10, 1),
            "o_to_c": ("orbs", "coins", 1, 10),
        }
        if custom_id in mapping:
            from_type, to_type, per_from, per_to = mapping[custom_id]
            user_id = str(interaction.user.id)
            balances = {
                "coins": get_total_coins(user_id),
                "diamond": get_total_diamonds(user_id),
                "orbs": get_total_orbs(user_id),
                "stars": get_total_stars(user_id),
            }
            await interaction.response.send_modal(
                ExchangeAmountModal(from_type=from_type, to_type=to_type, per_from=per_from, per_to=per_to, balances=balances)
            )
            return False
        return False


class ExchangeAmountModal(discord.ui.Modal):
    def __init__(self, from_type: str, to_type: str, per_from: int, per_to: int, balances: dict):
        title = f"Exchange {self._icon(from_type)} → {self._icon(to_type)}"
        super().__init__(title=title, timeout=120)
        self.from_type = from_type
        self.to_type = to_type
        self.per_from = int(per_from)
        self.per_to = int(per_to)
        self.balances = balances
        self.max_source_now = self._compute_max_source()
        fee_line = "Fee: **5%** of exchanged 🪙 (coins), charged in coins." if self.from_type == "coins" else "Fee: No fee."
        rate_line = f"Rate: {self.per_from} {self._icon(self.from_type)} → {self.per_to} {self._icon(self.to_type)}"
        bal_from = self.balances.get(self.from_type, 0)
        bal_to = self.balances.get(self.to_type, 0)
        info_lines = [
            rate_line,
            fee_line,
            f"Your balance: {bal_from} {self._icon(self.from_type)} | {bal_to} {self._icon(self.to_type)}",
            f"Max you can exchange now: {self.max_source_now} {self._icon(self.from_type)}",
            "Note: Submitting will immediately perform the exchange if eligible.",
            "Note: If you enter more than the max, the request will be rejected.",
        ]
        self.info = discord.ui.TextInput(label="Details", style=discord.TextStyle.paragraph, default="\n".join(info_lines), required=False)
        self.amount_input = discord.ui.TextInput(label=f"How many {self._icon(self.from_type)} to exchange?",
                                                 placeholder=f"Whole number (rate {self.per_from}→{self.per_to})",
                                                 required=True, min_length=1, max_length=18)
        self.add_item(self.info)
        self.add_item(self.amount_input)

    @staticmethod
    def _icon(t: str) -> str:
        return {"coins": "🪙", "orbs": "🔮", "diamond": "💎", "stars": "⭐"}.get(t, "❓")

    @staticmethod
    def _get_balance(user_id: str, currency: str) -> int:
        if currency == "coins":
            return get_total_coins(user_id)
        if currency == "diamond":
            return get_total_diamonds(user_id)
        if currency == "orbs":
            return get_total_orbs(user_id)
        if currency == "stars":
            return get_total_stars(user_id)
        return 0

    @staticmethod
    def _add_balance(user_id: str, currency: str, delta: int, reason: str):
        if currency == "coins":
            update_coins(user_id, delta, reason)
        elif currency == "diamond":
            update_diamonds(user_id, delta, reason)
        elif currency == "orbs":
            update_orbs(user_id, delta, reason)
        elif currency == "stars":
            update_stars(user_id, delta, reason)

    def _compute_max_source(self) -> int:
        source_balance = self.balances.get(self.from_type, 0)
        if self.from_type != "coins":
            return (source_balance // self.per_from) * self.per_from
        if source_balance <= 0:
            return 0
        def total_cost(batches: int) -> int:
            exchanged = batches * self.per_from
            fee = max(1, math.ceil(exchanged * 0.05)) if exchanged > 0 else 0
            return exchanged + fee
        approx_batches = int(source_balance // (self.per_from * 1.05))
        b = approx_batches
        while total_cost(b + 1) <= source_balance:
            b += 1
        while b > 0 and total_cost(b) > source_balance:
            b -= 1
        return b * self.per_from

    async def on_submit(self, interaction: discord.Interaction):
        raw = str(self.amount_input.value).strip().replace(",", "").replace("_", "")
        try:
            requested_from = int(raw)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a whole number.", ephemeral=True)
            return
        if requested_from <= 0:
            await interaction.response.send_message("❌ Amount must be at least 1.", ephemeral=True)
            return
        batches = requested_from // self.per_from
        if batches < 1:
            await interaction.response.send_message(
                f"🙅 You need at least **{self.per_from} {self._icon(self.from_type)}** to get **{self.per_to} {self._icon(self.to_type)}**.",
                ephemeral=True
            )
            return
        required_from = batches * self.per_from
        to_units = batches * self.per_to
        remainder = requested_from - required_from
        fee = max(1, math.ceil(required_from * 0.05)) if self.from_type == "coins" else 0
        total_cost_from = required_from + fee if self.from_type == "coins" else required_from
        user_id = str(interaction.user.id)
        bal_from = self._get_balance(user_id, self.from_type)
        bal_to = self._get_balance(user_id, self.to_type)
        if total_cost_from > bal_from:
            current_balances = {
                "coins": get_total_coins(user_id),
                "diamond": get_total_diamonds(user_id),
                "orbs": get_total_orbs(user_id),
                "stars": get_total_stars(user_id),
            }
            max_now = ExchangeAmountModal(from_type=self.from_type, to_type=self.to_type, per_from=self.per_from, per_to=self.per_to, balances=current_balances)._compute_max_source()
            need_icon = self._icon(self.from_type)
            fee_note = f" (incl. {fee} fee)" if self.from_type == "coins" else ""
            await interaction.response.send_message(
                f"🙅 Not enough {need_icon}. You tried **{required_from}{fee_note}**, but you only have **{bal_from} {need_icon}**.\n"
                f"Max you can exchange right now: **{max_now} {need_icon}**.",
                ephemeral=True
            )
            return
        if self.from_type == "coins":
            self._add_balance(user_id, "coins", -total_cost_from, "exchange out")
            self._add_balance(user_id, self.to_type, to_units, "exchange in")
            new_from = bal_from - total_cost_from
            new_to = bal_to + to_units
        elif self.to_type == "coins":
            self._add_balance(user_id, self.from_type, -required_from, "exchange out")
            self._add_balance(user_id, "coins", to_units, "exchange in")
            new_from = bal_from - required_from
            new_to = bal_to + to_units
        else:
            await interaction.response.send_message("🙅 Invalid exchange direction.", ephemeral=True)
            return
        if not interaction.response.is_done():
            await interaction.response.defer()
        channel = interaction.client.get_channel(LOGS_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title=f"{required_from} {self._icon(self.from_type)} → {to_units} {self._icon(self.to_type)}",
                                  description="✅ Exchange complete", color=discord.Color.green())
            embed.add_field(name="User", value=interaction.user.display_name, inline=True)
            if fee > 0:
                embed.add_field(name="Fee", value=f"{fee} {self._icon(self.from_type)} (5%)", inline=True)
            details = [
                f"{self._icon(self.from_type)} used: {required_from}",
                f"{self._icon(self.to_type)} gained: {to_units}",
                f"Remainder (not exchanged): {remainder} {self._icon(self.from_type)}" if remainder > 0 else None,
                f"New balances → {self._icon(self.from_type)}: {new_from} | {self._icon(self.to_type)}: {new_to}",
            ]
            embed.add_field(name="Details", value="\n".join([d for d in details if d]), inline=False)
            await send_as_webhook(channel, "currency_exchange", embed=embed)


def build_currency_exchange_shop():
    description = ("Trade safely between currencies, or contact staff for cash conversions." "\u200e")
    embed = generate_shop_embed(title="💱 Currency Exchange Shop", description=description, footer="", color=discord.Color.gold())
    embed.add_field(
        name="🔁 Quick Exchange Options",
        value=(
            "• **🪙 1000 → 💎 1**\t• **💎 1 → 🪙 1000**\n"
            "• **🪙 100 → ⭐ 1**\t• **⭐ 1 → 🪙 100**\n"
            "• **🪙 10 → 🔮 1**\t\t• **🔮 1 → 🪙 10**"
        ),
        inline=False,
    )
    embed.add_field(name="💵 Dollars ⇄ 💎 Diamonds", value=("• **$5 → 💎 150**\n" "• **💎 150 → $5**\n"), inline=False)
    view = CurrencyExchangeShopView()
    return embed, view