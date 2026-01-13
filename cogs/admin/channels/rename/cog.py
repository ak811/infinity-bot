from __future__ import annotations
import discord
from discord.ext import commands

class RenameChannelCog(commands.Cog):
    """sudo_rename_channel <channel_id> <new_name>"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_rename_channel")
    @commands.has_permissions(administrator=True)
    async def sudo_rename_channel(self, ctx, channel_id: int, *, new_name: str):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("🙅 Invalid channel ID.")
            return
        try:
            old = channel.name
            await channel.edit(name=new_name)
            await ctx.send(f"✅ {channel.mention} renamed from **{old}** to **{new_name}**.")
        except discord.Forbidden:
            await ctx.send("🙅 I don't have permission to rename this channel.")
        except discord.HTTPException as e:
            await ctx.send(f"🙅 Failed to rename the channel: {e}")
        except Exception as e:
            await ctx.send(f"🙅 Unexpected error: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(RenameChannelCog(bot))
