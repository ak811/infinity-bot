# cogs/stats/main.py

import discord
from discord.ext import commands

from configs.helper import send_as_webhook

from .groups import (
    all_stats,
    words,
    reactions,
    birthdays,
)

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # === Parent Group Command ===
    @commands.group(name="stats", aliases=["s"], invoke_without_command=True)
    async def stats(self, ctx):

        embed = discord.Embed(title="📊 Stats Commands", color=discord.Color.green())
        embed.description = (
            "🧮 `!all` — Big picture stats for the whole server\n"
            "🗣️ `!words` — What words you use the most\n"
            "😄 `!reactions` — What reactions you used or received the most\n"
            "🏆 `!reactions top` — Top reactions\n"
            "🎭 `!roles` — Server roles\n"
            "🤝 `!cc` — Close connections (your inner circle)\n"
            "💞 `!bff` — Best friends in the server\n"
            "💔 `!ncc` — Super active… just not with you :D\n"
            "😬 `!nbff` — Worst enemies 👀\n"
            "🎂 `!birthdays` — Who’s celebrating soon?\n"
            "🚶‍➡️ `!invites` — Who invited how many?\n"
            "🔤 `!alias` — Quick command abbreviations\n"
            "\n"
            "➕ Tip: `!roles <query>` to list members in a role\n"
            "   e.g. `!roles 13-15`, `!roles north america`, `!roles she`\n"
        )
        await send_as_webhook(ctx, "stats", embed=embed)

    # === Register Subcommands (delegated to other modules) ===
    @commands.command(name="all")
    async def allstats_cmd(self, ctx):
        await all_stats.show_full_stats(ctx)

    @commands.command(name="words")
    async def words_cmd(self, ctx, member: discord.Member = None):
        await words.words(ctx, member)

    @commands.command(name="reactions")
    async def reactions_cmd(self, ctx, *args):
        await reactions.reactions_entry(self.bot, ctx, args)

    @commands.command(name="reactions_top")
    async def reactions_top_cmd(self, ctx):
        await reactions.top_reactions(self.bot, ctx)

    @commands.command(name="birthdays")
    async def birthdays_cmd(self, ctx):
        await birthdays.birthdays(ctx)

    # ===== ALIAS: global + stats subcommand =====
    async def _send_aliases(self, ctx):
        desc = (
            f"**⚡ Quick Command Aliases**\n"
            f"• `!p` → `!profile`\n"
            f"• `!c` → `!commands`\n"
            f"• `!b` → `!bank`\n"
            f"• `!s` → `!stats`\n"
            f"• `!l` → `!leaderboard`\n"
            f"• `!a` → `!alias`\n"
        )
        embed = discord.Embed(
            title="📜 Command Aliases",
            description=desc,
            color=discord.Color.gold()
        )
        embed.set_footer(text="Use these shortcuts to save time!")
        await send_as_webhook(ctx, "stats", embed=embed)

    @commands.command(name="alias", aliases=["a", "aliases"])
    async def alias_cmd(self, ctx):
        # Global usage: !alias / !a / !aliases
        await self._send_aliases(ctx)

    @stats.command(name="alias")
    async def stats_alias_cmd(self, ctx):
        # Subcommand usage: !stats alias
        await self._send_aliases(ctx)


# === SETUP ===
async def setup(bot):
    await bot.add_cog(StatsCog(bot))
