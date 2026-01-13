# cogs/birthdays/cog.py
from __future__ import annotations

from datetime import datetime, time as dtime

import discord
from discord.ext import commands, tasks

from configs.helper import send_as_webhook
from configs.config_channels import (
    BIRTHDAY_CHANNEL_ID,
    ANNOUNCEMENTS_CHANNEL_ID,
)
from .storage import load_birthdays
from .views import BirthdayDropdownView

class BirthdaysCog(commands.Cog):
    """Birthday registration UI + daily announcements."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # start the daily loop (runs within cog lifecycle)
        self.check_birthdays.start()

    # ── lifecycle ──────────────────────────────────────────────────────────────
    async def cog_unload(self):
        self.check_birthdays.cancel()

    @commands.Cog.listener("on_ready")
    async def _on_ready(self):
        # Register persistent view so custom_id callbacks work across restarts
        try:
            self.bot.add_view(BirthdayDropdownView(self.bot))
        except Exception:
            pass
        await self._ensure_birthday_message()

    # ── setup message ─────────────────────────────────────────────────────────
    async def _ensure_birthday_message(self):
        channel = self.bot.get_channel(BIRTHDAY_CHANNEL_ID)
        if not isinstance(channel, discord.TextChannel):
            print("🙅 BIRTHDAY_CHANNEL_ID not found or not a TextChannel.")
            return

        embed = discord.Embed(
            title="🎉 Birthday Party Registration 🎉",
            description=(
                "😭 Feeling forgotten on your birthday? No one to say *HBD*? Not even your grandma? 😩\n"
                "**Don't worry — I gotchu** 💘😂\n\n"
                "👇 Use the dropdowns below to register:\n"
                "🗓️ **Month** – Pick your birth month\n"
                "🔢 **Day** – The day the world was blessed with you 🎁\n\n"
                "When your day comes... I'll shout it from the rooftops! 🥳"
            ),
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Set your birthday and let the celebrations begin!")

        try:
            async for msg in channel.history(limit=10):
                if msg.author == self.bot.user:
                    await msg.edit(embed=embed, view=BirthdayDropdownView(self.bot))
                    print("✅ Birthday dropdown message updated.")
                    return
            await channel.send(embed=embed, view=BirthdayDropdownView(self.bot))
            print("✅ Birthday dropdown message posted.")
        except Exception as e:
            print(f"🙅 Error setting up birthday message: {e}")

    # ── daily loop ────────────────────────────────────────────────────────────
    @tasks.loop(time=dtime(hour=0, minute=0))  # 00:00 UTC
    async def check_birthdays(self):
        birthdays = load_birthdays()
        today = datetime.utcnow().strftime("%m-%d")
        for uid, bday in birthdays.items():
            if bday == today:
                user = self.bot.get_user(int(uid))
                channel = self.bot.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
                if user and isinstance(channel, discord.TextChannel):
                    content = f"## 🎉 Happy Birthday, {user.mention}! We hope it's an amazing day! 🥳🎈🎂"
                    await send_as_webhook(channel, "birthday", content=content)

    @check_birthdays.before_loop
    async def before_check_birthdays(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(BirthdaysCog(bot))
