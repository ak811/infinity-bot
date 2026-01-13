import discord
from datetime import datetime
import calendar

from configs.config_files import BIRTHDAYS_FILE
from utils.utils_json import load_json
from configs.helper import send_as_webhook


async def birthdays(ctx):
    async with ctx.typing():
        birthdays = load_json(BIRTHDAYS_FILE)
        if not birthdays:
            await ctx.send("🎂 No birthdays have been registered yet.")
            return

        # Organize by month
        months = {month: [] for month in calendar.month_name if month}
        for user_id, date_str in birthdays.items():
            try:
                dt = datetime.strptime(date_str, "%m-%d")
            except ValueError:
                continue  # Skip invalid entries
            month_name = dt.strftime("%B")
            day = dt.day

            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"<@{user_id}>"
            months[month_name].append((day, name))

        # Create embed
        embed = discord.Embed(title="🎉 Registered Birthdays", color=discord.Color.purple())
        for month, entries in months.items():
            if not entries:
                continue
            entries.sort()
            lines = [f"**{day}** — {name}" for day, name in entries]
            embed.add_field(name=f"📅 {month}", value="\n".join(lines), inline=True)

        await send_as_webhook(ctx, "birthday", embed=embed)
