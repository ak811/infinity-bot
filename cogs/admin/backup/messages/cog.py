from __future__ import annotations
import discord
from discord.ext import commands

class BackupMessagesCog(commands.Cog):
    """sudo_backup_messages #source #destination — Copy recent messages from one channel to another."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_backup_messages")
    @commands.has_permissions(administrator=True)
    async def sudo_backup_messages(self, ctx: commands.Context, source_channel: discord.TextChannel, destination_channel: discord.TextChannel):
        await ctx.send(f"Starting backup from {source_channel.mention} to {destination_channel.mention}...")
        async for msg in source_channel.history(limit=1000):
            content = f"**{msg.author.name}:** {msg.content}"
            await destination_channel.send(content)
            for attachment in msg.attachments:
                await destination_channel.send(attachment.url)
        await ctx.send(f"Backup from {source_channel.mention} to {destination_channel.mention} completed!")

async def setup(bot: commands.Bot):
    await bot.add_cog(BackupMessagesCog(bot))
