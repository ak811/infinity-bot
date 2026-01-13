from __future__ import annotations
import discord
from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class RemoveButtonsCog(commands.Cog):
    """sudo_remove_buttons <channel_id> <message_id> — Strip view from a message."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_remove_buttons")
    @commands.has_permissions(administrator=True)
    async def sudo_remove_buttons(self, ctx: commands.Context, channel_id: int, message_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("🙅 Channel not found.")
            return
        try:
            msg = await channel.fetch_message(message_id)
            await msg.edit(view=None)
            log.info("Removed buttons from %s", msg.id)
            await ctx.send("✅ Buttons removed successfully!")
        except discord.NotFound:
            await ctx.send("🙅 Message not found. Check the ID.")
        except discord.Forbidden:
            await ctx.send("🙅 I don't have permission to edit this message.")
        except discord.HTTPException:
            await ctx.send("🙅 Failed to edit the message. Try again later.")

async def setup(bot: commands.Bot):
    await bot.add_cog(RemoveButtonsCog(bot))
