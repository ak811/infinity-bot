import psutil
from discord.ext import commands

class PCStatusCog(commands.Cog):
    """sudo_pc_status — Show CPU/RAM usage of the host."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_pc_status")
    @commands.has_permissions(administrator=True)
    async def sudo_pc_status(self, ctx):
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        await ctx.send(f"🖥️ CPU: {cpu}% | 💾 RAM: {mem}%")

async def setup(bot: commands.Bot):
    await bot.add_cog(PCStatusCog(bot))
