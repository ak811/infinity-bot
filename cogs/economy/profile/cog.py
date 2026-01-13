# cogs/economy/profile/cog.py
from __future__ import annotations

import discord
from discord.ext import commands
from discord.utils import get

from cogs.economy.coin.service import get_total_coins
from cogs.economy.orb.service import get_total_orbs
from cogs.economy.star.service import get_total_stars
from cogs.economy.diamond.service import get_total_diamonds
from cogs.economy.dollar.service import get_total_dollars

from cogs.server.roles.rank import get_highest_loot_legends_role_index
from cogs.economy.xp.service import get_total_xp
from configs.helper import send_as_webhook, PERSONAS
from configs.config_roles import LOOT_AND_LEGENDS_ROLES, MEMBER_ROLE_ID
from configs.config_general import BOT_USER_ID


class ProfileCog(commands.Cog):
    """!profile — display role/rank/xp and currency breakdown + total USD."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="profile", aliases=["p"])
    async def profile(self, ctx: commands.Context, *, arg: str | None = None):
        async with ctx.typing():
            # Determine target strictly by mention rules
            if arg is None:
                # plain !p -> author
                member = ctx.author
            else:
                if not ctx.message.mentions:
                    # Arg provided but no mentions -> tell them to mention using a normal embed (not webhook)
                    err = discord.Embed(
                        title="Mention required",
                        description="🙅 Please mention a user (e.g. `!p @username`). "
                                    "Names and IDs aren’t accepted.",
                        color=discord.Color.red()
                    )
                    await ctx.send(embed=err)
                    return
                # Use first mentioned user
                member = ctx.message.mentions[0]

            # Disallow targeting the bot
            if member.id == BOT_USER_ID:
                err = discord.Embed(
                    title="Not a user profile",
                    description="🤖 This command is for user profiles only.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=err)
                return

            total_coins = get_total_coins(member.id)
            orbs        = get_total_orbs(member.id)
            stars       = get_total_stars(member.id)
            diamonds    = get_total_diamonds(member.id)

            # Ensure XP is integer (no decimals shown anywhere)
            xp_raw      = get_total_xp(member.id)
            xp          = int(xp_raw)

            usd = get_total_dollars(member.id, return_breakdown=True)
            coins_usd, orbs_usd, stars_usd, diamonds_usd, total_usd = (
                usd["coins"], usd["orbs"], usd["stars"], usd["diamonds"], usd["total"]
            )

            members_data = []
            for m in ctx.guild.members:
                if not m.bot:
                    role_index  = get_highest_loot_legends_role_index(m)
                    # Cast to int so rank comparisons are on whole XP, avoiding float oddities/decimals
                    xp_score    = int(get_total_xp(m.id))
                    coins_score = get_total_coins(m.id)
                    members_data.append((m, role_index, xp_score, coins_score))
            sorted_members = sorted(members_data, key=lambda x: (x[1], x[2], x[3]), reverse=True)
            rank = next((i + 1 for i, (m, _, _, _) in enumerate(sorted_members) if m.id == member.id), "Unranked")

            role_index = get_highest_loot_legends_role_index(member)
            if role_index == -1:
                highest_role = get(ctx.guild.roles, id=MEMBER_ROLE_ID)
            else:
                highest_role_id = LOOT_AND_LEGENDS_ROLES[role_index][0]
                highest_role = get(ctx.guild.roles, id=highest_role_id)

            if member.avatar:
                avatar_url = member.display_avatar.url
            else:
                if ctx.guild.icon:
                    try:
                        avatar_url = ctx.guild.icon.with_size(128).url
                    except AttributeError:
                        avatar_url = ctx.guild.icon.url
                else:
                    avatar_url = member.default_avatar.url

            embed = discord.Embed(title=f"{member.display_name}'s Profile", color=discord.Color.blue())
            embed.set_thumbnail(url=avatar_url)

            embed.add_field(name="🎭 Role", value=(highest_role.name if highest_role else "No role"), inline=True)
            embed.add_field(
                name="🏆 Rank",
                value=f"#{rank} (out of {len(sorted_members)})" if isinstance(rank, int) else "Unranked",
                inline=True
            )
            # XP is now always whole-number formatted
            embed.add_field(name="🌟 XP", value=f"{xp:,}", inline=True)

            embed.add_field(name="🪙 Coins",    value=f"{total_coins:,}  (${coins_usd:.2f})", inline=True)
            embed.add_field(name="🔮 Orbs",     value=f"{orbs:,}  (${orbs_usd:.2f})", inline=True)
            embed.add_field(name="⭐ Stars",     value=f"{stars:,}  (${stars_usd:.2f})", inline=True)
            embed.add_field(name="💎 Diamonds", value=f"{diamonds:,}  (${diamonds_usd:.2f})", inline=True)

            embed.add_field(name="💵 Total Dollars", value=f"**${total_usd:,.2f}**", inline=True)

            # Send actual profile via webhook persona (unchanged)
            PERSONAS["custom"] = {"name": member.display_name, "avatar": avatar_url}
            await send_as_webhook(ctx, pet_type="custom", embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(ProfileCog(bot))
