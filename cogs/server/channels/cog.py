# cogs/server/channels/cog.py
from __future__ import annotations

from typing import List, Dict
from collections import defaultdict
import discord
from discord.ext import commands

from configs.config_roles import LOOT_AND_LEGENDS_ROLES, MEMBER_ROLE_ID

class ChannelsCog(commands.Cog):
    """
    !channels — show text/voice channels and the lowest LOOT role that can view them,
    grouped by category (excludes 'No Category').
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(
        name="channels",
        aliases=["ch", "chs", "chan", "listchannels"]
    )
    async def channels(self, ctx: commands.Context):
        """Show each text/voice channel and the lowest LOOT role that can view it, grouped by category (excludes No Category)."""
        guild: discord.Guild | None = ctx.guild
        if guild is None:
            return await ctx.reply("This command can only be used in a server.")

        # Whitelist roles present in this guild
        loot_roles: List[discord.Role] = []
        for role_id, *_ in LOOT_AND_LEGENDS_ROLES:
            r = guild.get_role(role_id)
            if r:
                loot_roles.append(r)

        if not loot_roles:
            return await ctx.reply("None of the LOOT_AND_LEGENDS roles exist in this server.")

        # Sort by Discord hierarchy (lowest → highest)
        loot_roles.sort(key=lambda r: r.position)

        # Helper: lowest whitelisted role that can view a channel
        def lowest_view_role_for(channel: discord.abc.GuildChannel):
            for role in loot_roles:
                perms: discord.Permissions = channel.permissions_for(role)
                if perms.view_channel:
                    return role
            return None

        # Gather text + voice channels
        all_channels: List[discord.abc.GuildChannel] = list(guild.text_channels) + list(guild.voice_channels)

        by_category: Dict[str, List[str]] = defaultdict(list)

        # Category positions for sorting
        category_positions: Dict[discord.CategoryChannel, int] = {}
        for cat in guild.categories:
            category_positions[cat] = cat.position

        for channel in all_channels:
            lowest_role = lowest_view_role_for(channel)
            if not lowest_role:
                continue  # skip channels where none of the LOOT roles can view

            # Skip "No Category"
            if channel.category is None:
                continue

            # Check if @everyone can view
            everyone_can_view = channel.permissions_for(guild.default_role).view_channel
            if everyone_can_view:
                suffix = f"<@&{MEMBER_ROLE_ID}>"
            else:
                suffix = lowest_role.mention

            line = f"• <#{channel.id}> — {suffix}"

            cat_name = channel.category.name
            by_category[cat_name].append(line)

        if not by_category:
            return await ctx.reply("No categorized channels are viewable by the specified roles.")

        # ---------- embed building & safe chunking ----------
        def chunk_lines(lines: List[str], max_len: int = 1000):
            chunk, length = [], 0
            for line in lines:
                ln = len(line) + 1
                if chunk and length + ln > max_len:
                    yield "\n".join(chunk)
                    chunk, length = [line], ln
                else:
                    chunk.append(line)
                    length += ln
            if chunk:
                yield "\n".join(chunk)

        def new_embed():
            e = discord.Embed(
                title="Server Channels by Level Roles",
                color=discord.Color.blurple(),
            )
            return e

        # Sort categories by their position
        def cat_pos_by_name(name: str) -> int:
            cat_obj = next((c for c in guild.categories if c.name == name), None)
            return category_positions.get(cat_obj, 9999)

        sorted_categories = sorted(by_category.keys(), key=cat_pos_by_name)

        embed = new_embed()
        field_count = 0
        embeds_to_send: List[discord.Embed] = []

        for cat_name in sorted_categories:
            lines = by_category[cat_name]
            if not lines:
                continue
            for i, chunk in enumerate(chunk_lines(lines, max_len=1000), start=1):
                field_name = cat_name if i == 1 else f"{cat_name} (cont.)"
                if field_count >= 25:
                    embeds_to_send.append(embed)
                    embed = new_embed()
                    field_count = 0
                embed.add_field(name=field_name, value=chunk, inline=False)
                field_count += 1

        if field_count > 0:
            embeds_to_send.append(embed)

        for e in embeds_to_send:
            await ctx.send(embed=e)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelsCog(bot))
