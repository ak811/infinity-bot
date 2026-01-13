# cogs/stats/logging/delete/core.py
from __future__ import annotations

from datetime import datetime, timezone
import discord
from configs.config_logging import logging
from configs.config_channels import BOT_PLAYGROUND_CHANNEL_ID


async def log_message_delete(bot: discord.Client, message: discord.Message) -> None:
    """
    Core delete logger. Safe to call from a Cog listener or elsewhere.
    """
    # Ignore bot messages and DM deletions
    if message.guild is None or message.author.bot:
        return

    try:
        channel = bot.get_channel(BOT_PLAYGROUND_CHANNEL_ID) or await bot.fetch_channel(BOT_PLAYGROUND_CHANNEL_ID)
        if isinstance(channel, (discord.TextChannel, discord.Thread)):
            embed = discord.Embed(
                title="🗑️ Message Deleted",
                description=(
                    f"**Author:** {message.author.mention}\n"
                    f"**Channel:** {message.channel.mention}"
                ),
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc),
            )
            embed.add_field(
                name="Content",
                value=message.content[:1024] if message.content else "*(no text content)*",
                inline=False,
            )
            await channel.send(embed=embed)
    except Exception as e:
        logging.warning(f"[DeleteLog] Failed to log deleted message: {e}")
