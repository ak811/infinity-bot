# cogs/birthdays/views.py
from __future__ import annotations

import calendar
from datetime import datetime
from typing import Dict, Optional

import discord
from discord.ui import View, Select, Button

from configs.config_channels import BOT_PLAYGROUND_CHANNEL_ID
from .storage import load_birthdays, save_birthdays

# Shared month map (string keys to match saved format)
MONTH_MAP: Dict[str, str] = {
    "01": "January", "02": "February", "03": "March",     "04": "April",
    "05": "May",     "06": "June",     "07": "July",      "08": "August",
    "09": "September","10": "October", "11": "November",  "12": "December",
}

# In-memory cache; always persist via save_birthdays()
_birthdays: Dict[str, str] = load_birthdays()

# ─── UI Elements ───────────────────────────────────────────────────────────────
class MonthSelect(Select):
    def __init__(self):
        opts = [
            discord.SelectOption(label=month, value=str(i).zfill(2))
            for i, month in enumerate(MONTH_MAP.values(), start=1)
        ]
        super().__init__(placeholder="🗓️ Select your birth month", options=opts, custom_id="birthday_month")

    async def callback(self, interaction: discord.Interaction):
        assert isinstance(self.view, BirthdayDropdownView)
        self.view.selected_month = self.values[0]
        await interaction.response.send_message("✅ Month selected! Now pick your day.", ephemeral=True)


class DaySelectPart1(Select):
    def __init__(self):
        opts = [discord.SelectOption(label=str(d), value=str(d).zfill(2)) for d in range(1, 16)]
        super().__init__(placeholder="🔢 Day (1–15)", options=opts, custom_id="birthday_day_1")

    async def callback(self, interaction: discord.Interaction):
        assert isinstance(self.view, BirthdayDropdownView)
        self.view.selected_day = self.values[0]
        await self.view.register_birthday(interaction)


class DaySelectPart2(Select):
    def __init__(self):
        opts = [discord.SelectOption(label=str(d), value=str(d).zfill(2)) for d in range(16, 32)]
        super().__init__(placeholder="🔢 Day (16–31)", options=opts, custom_id="birthday_day_2")

    async def callback(self, interaction: discord.Interaction):
        assert isinstance(self.view, BirthdayDropdownView)
        self.view.selected_day = self.values[0]
        await self.view.register_birthday(interaction)


class ClearBirthdayButton(Button):
    def __init__(self):
        super().__init__(label="Clear My Birthday", style=discord.ButtonStyle.secondary, custom_id="clear_birthday")

    async def callback(self, interaction: discord.Interaction):
        assert isinstance(self.view, BirthdayDropdownView)
        user_id = str(interaction.user.id)

        if user_id in _birthdays:
            del _birthdays[user_id]
            save_birthdays(_birthdays)

            # reset local state + refresh view
            self.view.selected_month = self.view.selected_day = None
            try:
                await interaction.message.edit(view=BirthdayDropdownView(self.view.bot))
            except Exception:
                pass

            await interaction.response.send_message(
                "🧼 Your birthday has been cleared and dropdowns have been reset!", ephemeral=True
            )

            # audit
            log_channel = self.view.bot.get_channel(BOT_PLAYGROUND_CHANNEL_ID)
            if isinstance(log_channel, discord.TextChannel):
                embed = discord.Embed(
                    title="🙅 Birthday Cleared",
                    description=f"{interaction.user.mention} **cleared their birthday.**",
                    color=discord.Color.red(),
                )
                embed.set_thumbnail(url=interaction.user.display_avatar.url)
                embed.set_footer(text=f"User ID: {interaction.user.id}")
                await log_channel.send(embed=embed)
        else:
            await interaction.response.send_message("⚠️ You haven't set a birthday yet.", ephemeral=True)


class ShowAllBirthdaysButton(Button):
    def __init__(self):
        super().__init__(label="Show All Birthdays 🎁", style=discord.ButtonStyle.secondary, custom_id="show_birthdays")

    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
        except (discord.InteractionResponded, discord.NotFound):
            return

        if not _birthdays:
            await interaction.followup.send("🎂 No birthdays have been registered yet.", ephemeral=True)
            return

        months: Dict[str, list[tuple[int, str]]] = {m: [] for m in calendar.month_name if m}
        for user_id, date_str in _birthdays.items():
            try:
                dt = datetime.strptime(date_str, "%m-%d")
                month_name = dt.strftime("%B")
                day = dt.day
                member = interaction.guild.get_member(int(user_id)) if interaction.guild else None
                name = member.display_name if member else f"<@{user_id}>"
                months[month_name].append((day, name))
            except Exception:
                continue

        embed = discord.Embed(
            title="🎉 Registered Birthdays",
            description="Here are all registered birthdays by month:",
            color=discord.Color.purple(),
        )

        for month, entries in months.items():
            if not entries:
                continue
            entries.sort()
            lines = [f"**{day}** — {name}" for day, name in entries]
            embed.add_field(name=f"📅 {month}", value="\n".join(lines[:20]), inline=True)

        await interaction.followup.send(embed=embed, ephemeral=True)


# ─── Main View ────────────────────────────────────────────────────────────────
class BirthdayDropdownView(View):
    def __init__(self, bot: discord.Client):
        super().__init__(timeout=None)  # persistent components
        self.bot = bot
        self.selected_month: Optional[str] = None
        self.selected_day: Optional[str] = None
        self.add_item(MonthSelect())
        self.add_item(DaySelectPart1())
        self.add_item(DaySelectPart2())
        self.add_item(ClearBirthdayButton())
        self.add_item(ShowAllBirthdaysButton())

    async def register_birthday(self, interaction: discord.Interaction):
        if not (self.selected_month and self.selected_day):
            await interaction.response.send_message("⚠️ Please select both month and day.", ephemeral=True)
            return

        date_str = f"{self.selected_month}-{self.selected_day}"
        _birthdays[str(interaction.user.id)] = date_str
        save_birthdays(_birthdays)

        month_name = MONTH_MAP[self.selected_month]
        readable_date = f"{month_name} {int(self.selected_day)}"

        await interaction.response.send_message(f"🎉 Birthday registered as **{readable_date}**!", ephemeral=True)

        log_channel = self.bot.get_channel(BOT_PLAYGROUND_CHANNEL_ID)
        if isinstance(log_channel, discord.TextChannel):
            embed = discord.Embed(
                title="🎂 Birthday Registered!",
                description=f"{interaction.user.mention} set their birthday to **{readable_date}**.",
                color=discord.Color.magenta(),
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"User ID: {interaction.user.id}")
            await log_channel.send(embed=embed)
