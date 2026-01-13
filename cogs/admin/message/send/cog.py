import discord
from discord.ext import commands

class SendMessageCog(commands.Cog):
    """sudo_send_message #channel message — Send a message into a channel."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_send_message")
    @commands.has_permissions(administrator=True)
    async def sudo_send_message(self, ctx, channel: discord.TextChannel, *, message: str):
        if not channel.permissions_for(ctx.guild.me).send_messages:
            await ctx.send(f"⚠️ I don't have permission to send messages in {channel.mention}.")
            return
        try:
            await channel.send(message)
            await ctx.send(f"✅ Message sent to {channel.mention}.")
        except discord.Forbidden:
            await ctx.send(f"⚠️ I don't have permission to send messages in {channel.mention}.")
        except discord.HTTPException as e:
            await ctx.send(f"⚠️ Failed to send the message: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SendMessageCog(bot))
