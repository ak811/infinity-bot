from __future__ import annotations
import discord
from discord.ext import commands
import logging

log = logging.getLogger(__name__)

class PurgeCog(commands.Cog):
    """sudo_purge <count> OR sudo_purge <start_id> <end_id> [@user] [#channel]"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_purge")
    @commands.has_permissions(administrator=True)
    async def sudo_purge(self, ctx: commands.Context, *args):
        if not args:
            await ctx.send("Usage: !sudo_purge <count> OR !sudo_purge <start_id> <end_id> [@user] [#channel]")
            return

        def is_big_id(s: str):
            try:
                return len(s) >= 16 and int(s)
            except Exception:
                return False

        # range mode
        if len(args) >= 2 and is_big_id(args[0]) and is_big_id(args[1]):
            start_id, end_id = int(args[0]), int(args[1])
            target_member = None
            target_channel = ctx.channel

            if len(args) >= 3:
                try:
                    target_member = await commands.MemberConverter().convert(ctx, args[2])
                except Exception:
                    await ctx.send("Third argument must be a valid user mention.")
                    return
            if len(args) == 4:
                try:
                    target_channel = await commands.TextChannelConverter().convert(ctx, args[3])
                except Exception:
                    await ctx.send("Fourth argument must be a valid text channel.")
                    return

            def check(msg: discord.Message):
                return start_id <= msg.id <= end_id and (not target_member or msg.author.id == target_member.id)

            try:
                deleted = await target_channel.purge(limit=None, check=check)
                await ctx.send(f"🧹 Purged {len(deleted)} messages from {target_channel.mention}.", delete_after=5)
            except Exception as e:
                log.exception("[Purge] range mode failed", exc_info=e)
                await ctx.send("An error occurred while purging messages.")
            return

        # count mode
        try:
            count = int(args[0].strip())
            target_channel = ctx.channel
        except Exception:
            await ctx.send("First argument must be a number (e.g., `!sudo_purge 10`).")
            return

        try:
            deleted = await target_channel.purge(limit=count)
            await ctx.send(f"🧹 Purged {len(deleted)} messages from {target_channel.mention}.", delete_after=5)
        except Exception as e:
            log.exception("[Purge] count mode failed", exc_info=e)
            await ctx.send("An error occurred while purging messages.")

async def setup(bot: commands.Bot):
    await bot.add_cog(PurgeCog(bot))
