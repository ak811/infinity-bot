from __future__ import annotations
import discord
from discord.ext import commands

DANGEROUS = [
    "administrator","manage_channels","manage_roles","manage_webhooks",
    "mention_everyone","manage_messages","manage_guild"
]

class CheckDangerousPermsCog(commands.Cog):
    """sudo_check_dangerous_perms — Scan @everyone overwrites for risky perms."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_check_dangerous_perms")
    @commands.has_permissions(administrator=True)
    async def sudo_check_dangerous_perms(self, ctx):
        report = []
        for ch in ctx.guild.channels:
            ow = ch.overwrites_for(ctx.guild.default_role)
            for p in DANGEROUS:
                if getattr(ow, p, False):
                    report.append(f"⚠️ `{p}` allowed in #{ch.name}")

        if not report:
            await ctx.send("✅ No dangerous permissions found for `@everyone` in any channel.")
        else:
            await ctx.send("🚨 Dangerous permissions for `@everyone` detected:\n" + "\n".join(report[:20]))
            if len(report) > 20:
                await ctx.send(f"...and {len(report) - 20} more.")

async def setup(bot: commands.Bot):
    await bot.add_cog(CheckDangerousPermsCog(bot))
