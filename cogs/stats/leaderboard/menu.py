# cogs/leaderboard/menu.py
from __future__ import annotations

import discord
from discord.ext import commands
from discord.ui import View, Select

from configs.config_files import ACTIVITY_DATA_FILE
from configs.config_channels import BOTS_PLAYGROUND_CHANNEL_ID
from configs.helper import send_as_webhook

from .manager import refresh_generic_leaderboard
from .rows import compute_coins_row, coins_sort_key, format_coins_row
from .rows_messages import make_messages_compute_fn, messages_sort_key, format_messages_row, MESSAGE_LEADERBOARD_FILE
from .rows_vc import make_vc_compute_fn, vc_sort_key, format_vc_row
from .rows_reactions import (
    make_reactions_compute_fn,
    reactions_sort_key,
    make_format_reactions_row,
    REACTIONS_GIVEN_FILE,
    REACTIONS_RECEIVED_FILE,
)


class LeaderboardCog(commands.Cog):
    """All leaderboard commands, slim and modular."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    class LeaderboardMenu(View):
        def __init__(self, cog: "LeaderboardCog", ctx: commands.Context):
            super().__init__(timeout=None)
            self.cog = cog
            self.ctx = ctx
            self.add_item(LeaderboardCog.LeaderboardSelect(cog, ctx, parent_view=self))

    class LeaderboardSelect(Select):
        def __init__(self, cog: "LeaderboardCog", ctx: commands.Context, parent_view: View):
            options = [
                discord.SelectOption(label="💰 Main Leaderboard", value="main"),
                discord.SelectOption(label="✉️ Messages Leaderboard", value="messages"),
                discord.SelectOption(label="🎙️ VC Leaderboard", value="vc"),
                discord.SelectOption(label="👍 Reactions Given", value="react_give"),
                discord.SelectOption(label="💖 Reactions Received", value="react_recv"),
            ]
            super().__init__(placeholder="Select a leaderboard…", min_values=1, max_values=1, options=options)
            self.cog = cog
            self.ctx = ctx
            self.parent_view = parent_view

        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != self.ctx.author.id:
                embed = discord.Embed(
                    title="That's Not Yours!",
                    description="Uh oh! That message doesn't belong to you.\nYou must run this command to interact with it.",
                    color=discord.Color.orange(),
                )
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            async def build_paginated(key, title, file, compute_fn, sort_fn, format_fn):
                # Build pages ONLY; keep this message ephemeral/personal via the menu
                _, pages = await refresh_generic_leaderboard(
                    bot=self.cog.bot,
                    title=title,
                    message_id_key=f"temp_{key}_leaderboard_msg",
                    channel_id=interaction.channel.id,
                    compute_fn=compute_fn,
                    sort_key_fn=sort_fn,
                    format_fn=format_fn,
                    file=file,
                    post_to_channel=False,
                )
                if not pages:
                    return discord.Embed(description="No data available."), self.parent_view

                # locator for the paginator view
                def locate(u: discord.User | discord.Member):
                    for i, emb in enumerate(pages):
                        for f in emb.fields:
                            if f"<@{u.id}>" in f.value or f"<@!{u.id}>" in f.value:
                                return i
                    return None

                from .base_view import BaseLeaderboardView
                view = BaseLeaderboardView(pages, locate)
                view.add_item(self)  # keep the selector visible on each page
                return pages[0], view

            sel = self.values[0]
            if sel == "main":
                embed, view = await build_paginated(
                    "coins", "🏆 Leaderboard: Top Players",
                    ACTIVITY_DATA_FILE, compute_coins_row, coins_sort_key, format_coins_row,
                )
            elif sel == "messages":
                embed, view = await build_paginated(
                    "messages", "🏆 Message Leaderboard",
                    MESSAGE_LEADERBOARD_FILE, make_messages_compute_fn(MESSAGE_LEADERBOARD_FILE),
                    messages_sort_key, format_messages_row,
                )
            elif sel == "vc":
                embed, view = await build_paginated(
                    "vc", "🎙️ VC Leaderboard",
                    ACTIVITY_DATA_FILE, make_vc_compute_fn(ACTIVITY_DATA_FILE),
                    vc_sort_key, format_vc_row,
                )
            elif sel == "react_give":
                embed, view = await build_paginated(
                    "reactions_given", "👍 Reactions Given",
                    REACTIONS_GIVEN_FILE, make_reactions_compute_fn(REACTIONS_GIVEN_FILE),
                    reactions_sort_key, make_format_reactions_row("👍"),
                )
            elif sel == "react_recv":
                embed, view = await build_paginated(
                    "reactions_received", "💖 Reactions Received",
                    REACTIONS_RECEIVED_FILE, make_reactions_compute_fn(REACTIONS_RECEIVED_FILE),
                    reactions_sort_key, make_format_reactions_row("💖"),
                )
            else:
                embed, view = discord.Embed(description="Unknown leaderboard selection."), self.parent_view

            if interaction.response.is_done():
                await interaction.edit_original_response(embed=embed, view=view)
            else:
                await interaction.response.edit_message(embed=embed, view=view)

    @commands.command(name="leaderboard", help="Pick any leaderboard from the dropdown menu.", aliases=["l"])
    async def leaderboard_menu(self, ctx: commands.Context):
        view = self.LeaderboardMenu(self, ctx)
        embed = discord.Embed(
            title="📊 Pick a Leaderboard",
            description="Use the dropdown below to select which leaderboard you'd like to view.",
            color=discord.Color.blurple(),
        )
        await send_as_webhook(ctx, "leaderboard", embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardCog(bot))
