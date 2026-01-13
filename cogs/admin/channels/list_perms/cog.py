import discord
from discord.ext import commands

class ListPermsCog(commands.Cog):
    """sudo_list_perms — Show allowed/denied perms for @everyone for visible channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_list_perms")
    @commands.has_permissions(administrator=True)
    async def sudo_list_perms(self, ctx):
        everyone = ctx.guild.default_role
        sections = []
        for ch in ctx.guild.channels:
            if isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
                perms = ch.permissions_for(everyone)
                if perms.view_channel:
                    allowed = [p for p, v in perms if v]
                    denied  = [p for p, v in perms if not v]
                    sections.append(
                        f"**#{ch.name}**\n"
                        f"✅ Allowed: {', '.join(allowed)}\n"
                        f"🙅 Denied: {', '.join(denied)}\n"
                    )
        chunk = ""
        for s in sections:
            if len(chunk) + len(s) > 1900:
                await ctx.send(chunk)
                chunk = ""
            chunk += s + "\n"
        if chunk:
            await ctx.send(chunk)

async def setup(bot: commands.Bot):
    await bot.add_cog(ListPermsCog(bot))
