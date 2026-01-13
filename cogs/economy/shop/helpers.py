# cogs/shop/helpers.py
from __future__ import annotations

import discord
import logging
from utils.utils_json import load_json, save_json
from configs.config_files import SHOP_IDS_FILE


def generate_shop_embed(title: str, description: str, footer: str,
                        color: discord.Color, thumbnail: str | None = None) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=footer)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    return embed


async def update_shop_message(bot: discord.Client, channel_id: int, shop_key: str,
                              embed: discord.Embed, view: discord.ui.View):
    channel = bot.get_channel(channel_id)
    if channel is None:
        logging.error(f"Shop channel with ID {channel_id} not found.")
        return

    shop_ids = load_json(SHOP_IDS_FILE)
    bot.add_view(view)  # persistent view

    if shop_key in shop_ids:
        try:
            message = await channel.fetch_message(shop_ids[shop_key])
            await message.edit(embed=embed, view=view)
            logging.info(f"Updated shop message for {shop_key} in channel {channel_id}.")
        except Exception as e:
            logging.error(f"Failed to update shop message for {shop_key} in channel {channel_id}: {e}")
    else:
        logging.error(f"Shop key '{shop_key}' not found in SHOP_IDS_FILE.")