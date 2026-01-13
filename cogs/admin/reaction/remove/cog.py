import discord
from discord.ext import commands

class RemoveReactionCog(commands.Cog):
    """sudo_remove_reaction <channel_id> <message_id> <emoji>"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_remove_reaction")
    @commands.has_permissions(administrator=True)
    async def sudo_remove_reaction(self, ctx, channel_id: int, message_id: int, reaction: str):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await ctx.send("🙅 Invalid channel ID.")
            return
        try:
            msg = await channel.fetch_message(message_id)
            await msg.remove_reaction(reaction, self.bot.user)
            await ctx.send(f"✅ Removed reaction {reaction} in {channel.mention}.")
        except discord.NotFound:
            await ctx.send("🙅 Message not found.")
        except discord.Forbidden:
            await ctx.send("⚠️ I don't have permission to remove reactions in that channel.")
        except discord.HTTPException as e:
            await ctx.send(f"⚠️ Failed to remove the reaction: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(RemoveReactionCog(bot))
