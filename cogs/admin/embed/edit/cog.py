from __future__ import annotations
import discord
from discord.ext import commands

class EditEmbedCog(commands.Cog):
    """sudo_edit_embed <channel_id> <message_id> "<title>" "<description>" — Replace message with an embed."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_edit_embed")
    @commands.has_permissions(administrator=True, manage_messages=True)
    async def sudo_edit_embed(self, ctx: commands.Context, channel_id: int, message_id: int, title: str, *, description: str):
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                await ctx.send("🙅 Channel not found.")
                return
            message = await channel.fetch_message(message_id)
            if not message:
                await ctx.send("🙅 Message not found.")
                return
            embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
            await message.edit(content=None, embed=embed)
            await ctx.send("✅ Message updated with embed.")
        except Exception as e:
            await ctx.send(f"⚠️ Failed to edit message: `{e}`")

async def setup(bot: commands.Bot):
    await bot.add_cog(EditEmbedCog(bot))
