from __future__ import annotations
import re
import discord
from discord.ext import commands

def _split_message(s: str, max_len: int = 2000):
    return [s[i:i+max_len] for i in range(0, len(s), max_len)]

class BackupCategoryCog(commands.Cog):
    """sudo_backup_category <category_id> #destination — Backup all ticket channels in a category."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_backup_category")
    @commands.has_permissions(administrator=True)
    async def sudo_backup_category(self, ctx: commands.Context, category_id: int, destination_channel: discord.TextChannel):
        category = discord.utils.get(ctx.guild.categories, id=category_id)
        if not category:
            await ctx.send("Invalid category ID. Please check and try again.")
            return

        await ctx.send(f"Starting backup of `{category.name}` to {destination_channel.mention}...")
        for ch in category.text_channels:
            messages = [m async for m in ch.history(limit=1000)]
            if not messages:
                continue

            first = messages[-1]
            mention = re.findall(r"<@!?(\d+)>", first.content)
            if mention:
                await destination_channel.send(f"🎟️ **Ticket opened by:** <@{mention[0]}>")
            else:
                await destination_channel.send(f"🎟️ **Ticket opened in:** #{ch.name} (User not found)")

            for m in reversed(messages):
                content = f"**{m.author.name}:** {m.content}"
                if len(content) > 2000:
                    for part in _split_message(content):
                        await destination_channel.send(part)
                else:
                    await destination_channel.send(content)
                for a in m.attachments:
                    await destination_channel.send(a.url)

            await destination_channel.send("-------------------------------------------------------------------")

        await ctx.send(f"Backup for `{category.name}` completed in {destination_channel.mention}!")

async def setup(bot: commands.Bot):
    await bot.add_cog(BackupCategoryCog(bot))
