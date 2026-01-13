# cogs/leaderboard/manager.py
from __future__ import annotations

import time
import discord
from typing import Callable

from utils.utils_json import load_json, save_json
from configs.config_files import SHOP_IDS_FILE
from configs.config_general import BOT_GUILD_ID
from .base_view import BaseLeaderboardView


class LeaderboardManager:
    """
    Builds pages from a source file containing user ids.
    compute_fn(user_id, now, guild) -> row | None
    sort_key_fn(row) -> tuple for DESC sort
    format_fn(rank, row) -> str line
    """
    def __init__(
        self,
        guild: discord.Guild,
        channel: discord.abc.MessageableChannel,
        title: str,
        compute_fn: Callable[[int | str, float, discord.Guild], object | None],
        sort_key_fn: Callable[[object], tuple],
        format_fn: Callable[[int, object], str],
        message_id_key: str,
        file: str,
        items_per_page: int = 10,
    ):
        self.guild = guild
        self.channel = channel
        self.title = title
        self.compute_fn = compute_fn
        self.sort_key_fn = sort_key_fn
        self.format_fn = format_fn
        self.message_id_key = message_id_key
        self.items_per_page = items_per_page
        self.file = file
        self.pages: list[discord.Embed] = []

    async def build_pages(self) -> list[discord.Embed]:
        now = time.time()
        data = load_json(self.file, default_value={})
        rows = []
        for uid in set(map(str, data.keys())):
            if self.guild.me and str(uid) == str(self.guild.me.id):
                continue
            row = self.compute_fn(uid, now, self.guild)
            if row is not None:
                rows.append(row)

        rows.sort(key=self.sort_key_fn, reverse=True)

        pages: list[discord.Embed] = []
        for i in range(0, len(rows), self.items_per_page):
            embed = discord.Embed(title=self.title, color=discord.Color.gold())
            for rank, row in enumerate(rows[i:i + self.items_per_page], start=i + 1):
                embed.add_field(name="\u200b", value=self.format_fn(rank, row), inline=False)
            pages.append(embed)

        if not pages:
            pages = [discord.Embed(title=self.title, description="No data available.", color=discord.Color.gold())]
        self.pages = pages
        return pages

    async def post_or_update_first_page(self) -> discord.Message:
        shop_ids = load_json(SHOP_IDS_FILE, default_value={})
        message_id = shop_ids.get(self.message_id_key)
        message = None
        if message_id:
            try:
                message = await self.channel.fetch_message(message_id)
            except discord.NotFound:
                message = None

        if not message:
            message = await self.channel.send(embed=self.pages[0])
            shop_ids[self.message_id_key] = message.id
            save_json(SHOP_IDS_FILE, shop_ids)

        await message.edit(embed=self.pages[0])
        return message


async def refresh_generic_leaderboard(
    bot: discord.Client | discord.ext.commands.Bot,
    title: str,
    message_id_key: str,
    channel_id: int,
    compute_fn,
    sort_key_fn,
    format_fn,
    file: str,
    items_per_page: int = 10,
    post_to_channel: bool = True,
):
    """Build pages and optionally create/update a persistent channel message."""
    guild = bot.get_guild(BOT_GUILD_ID)
    channel = bot.get_channel(channel_id)
    if not guild or not channel:
        return None, None

    mgr = LeaderboardManager(
        guild=guild,
        channel=channel,
        title=title,
        compute_fn=compute_fn,
        sort_key_fn=sort_key_fn,
        format_fn=format_fn,
        message_id_key=message_id_key,
        file=file,
        items_per_page=items_per_page,
    )
    pages = await mgr.build_pages()

    message = None
    if post_to_channel:
        message = await mgr.post_or_update_first_page()

    def locate_user_callback(user: discord.User | discord.Member):
        for index, embed in enumerate(pages):
            for field in embed.fields:
                if f"<@{user.id}>" in field.value or f"<@!{user.id}>" in field.value:
                    return index
        return None

    view = BaseLeaderboardView(pages, locate_user_callback)
    if message:
        await message.edit(view=view)

    return message, pages
