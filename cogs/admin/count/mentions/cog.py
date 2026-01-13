from __future__ import annotations
import discord
from discord.ext import commands

class CountMentionsCog(commands.Cog):
    """sudo_count_mentions <channel_id> <search_phrase> — Count mentions in matching messages."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_count_mentions")
    @commands.has_permissions(administrator=True)
    async def sudo_count_mentions(self, ctx: commands.Context, channel_id: int, *, search_phrase: str):
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            await ctx.send("Channel not found!")
            return

        counts = {}
        async for m in channel.history(limit=None):
            if search_phrase in m.content and m.mentions:
                for mem in m.mentions:
                    uid = str(mem.id)
                    counts[uid] = counts.get(uid, 0) + 1

        await ctx.send(f"Counts: {counts}")

async def setup(bot: commands.Bot):
    await bot.add_cog(CountMentionsCog(bot))
