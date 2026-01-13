import discord
from discord.ext import commands

class EditMessageCog(commands.Cog):
    """sudo_edit_message #channel <message_id> <new_message> — Edit a bot-authored message."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_edit_message")
    @commands.has_permissions(administrator=True)
    async def sudo_edit_message(self, ctx, channel: discord.TextChannel, message_id: int, *, new_message: str):
        perms = channel.permissions_for(ctx.guild.me)
        if not (perms.read_message_history and perms.send_messages):
            await ctx.send(f"⚠️ I don't have permission to read or send in {channel.mention}.")
            return
        try:
            msg = await channel.fetch_message(message_id)
            if msg.author == self.bot.user:
                await msg.edit(content=new_message)
                await ctx.send(f"✅ Message edited in {channel.mention}.")
            else:
                await ctx.send("🙅 I can only edit messages that I authored.")
        except discord.NotFound:
            await ctx.send("🙅 Message not found.")
        except discord.Forbidden:
            await ctx.send(f"⚠️ I don't have permission to edit messages in {channel.mention}.")
        except discord.HTTPException as e:
            await ctx.send(f"⚠️ Failed to edit the message: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(EditMessageCog(bot))
