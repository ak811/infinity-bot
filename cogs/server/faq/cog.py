# cogs/server/faq/cog.py
from __future__ import annotations

import discord
from discord.ext import commands

class FAQCog(commands.Cog):
    """
    Displays a static list of FAQs with predefined answers (embed).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="faq", help="Displays a list of frequently asked questions.")
    async def faq(self, ctx: commands.Context):
        """
        Displays a static list of FAQs with predefined answers, using an embed.
        """
        faqs = {
            "What is this server about?":
                "🌟 **Infinity Café** is a cozy and energetic community where you can chat, level up, join clans, and flex your progress!",
            "How do I level up?":
                "Earn XP by chatting, spending time in VC, reacting, and joining events. Every few levels unlock new roles and perks!",
            "What are the level milestones?":
                "Skilled → Proficient → Specialist → Expert → Elite → Mastermind → Grandmaster → Champion → Legend ⚡",
            "How does the currency system work?":
                "💎 Earn **Coins**, **Orbs**, **Stars**, and **Diamonds** through chatting, VC time, events, and streaks. Spend your Diamonds in the 🏪 Shop for cool rewards and perks!",
            "What are clans and how do I join one?":
                "⚔️ Clans are your squads! Join one with `!clan join <name>` and contribute your activity to help your clan climb the weekly leaderboard for rewards.",
            "Where can I chat or hang out?":
                "🗨️ For casual chats, head to ⁠🐛・chitty-chat﹗ or 🧮・serious-chat﹗. Jump into VCs to study, jam, or chill — or join games and events!",
            "What are some useful commands?":
                "🚀 Try these: `!profile` (your stats), `!shop` (spend coins), and check ⁠⚓・commands﹗ for more!",
            "Who made the bot?":
                "☕ Brewed with ❤️ by **alex.k**",
        }

        embed = discord.Embed(
            title="📚 Infinity Café — FAQs",
            description="Here are some of the most frequently asked questions:",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}",
            icon_url=ctx.author.display_avatar.url,
        )

        for question, answer in faqs.items():
            embed.add_field(name=f"**Q:** {question}", value=answer, inline=False)

        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(FAQCog(bot))
