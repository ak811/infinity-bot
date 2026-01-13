# pycord/queue/commands.py

import discord
from discord.ext import commands
from cogs.server.roles.rank import get_highest_loot_legends_role_index
from configs.helper import send_as_webhook
from configs.config_logging import logging

from .state import queue_state
from .views import QueueView, update_queue_embed, send_queue_status

MIN_CLEAR_INDEX = 4  # Elite or higher (adjust if needed)


class _AwaitableNoop:
    """An object that can be awaited (completes immediately) but is harmless if ignored."""
    def __await__(self):
        return iter(())


def _find_related_vc(guild: discord.Guild, text_channel: discord.abc.GuildChannel):
    if not getattr(text_channel, "category_id", None):
        return None
    for vc in guild.voice_channels:
        if vc.category_id == text_channel.category_id:
            return vc
    return None


def setup_queue_commands(bot: commands.Bot):

    @bot.command(name="q")
    async def queue_cmd(ctx: commands.Context, subcommand: str = None):
        vc = _find_related_vc(ctx.guild, ctx.channel)
        if not vc:
            await send_as_webhook(
                ctx,
                "queue",
                embed=discord.Embed(
                    description="🙅 Use this in a text channel under a VC category.",
                    color=discord.Color.red()
                )
            )
            return

        vc_id = vc.id

        if subcommand == "clear":
            user_index = get_highest_loot_legends_role_index(ctx.author)
            if user_index < MIN_CLEAR_INDEX:
                await send_as_webhook(
                    ctx,
                    "queue",
                    embed=discord.Embed(
                        description="🙅 You need to be **Elite** or higher to clear the queue.",
                        color=discord.Color.red()
                    )
                )
                return
            if vc_id in queue_state:
                queue_state[vc_id]["user_ids"].clear()
                await update_queue_embed(ctx.guild, vc_id)
            await send_as_webhook(
                ctx,
                "queue",
                embed=discord.Embed(
                    description="✅ Queue cleared.",
                    color=discord.Color.green()
                )
            )
            return

        if vc_id in queue_state:
            await send_queue_status(ctx, vc_id)
            return

        embed = discord.Embed(
            title="🎮 Current Queue",
            description="_(empty)_",
            color=discord.Color.green()
        )
        view = QueueView(vc_id)
        msg = await send_as_webhook(ctx, "queue", embed=embed, view=view)

        queue_state[vc_id] = {
            "user_ids": [],
            "message_id": msg.id,
            "channel_id": ctx.channel.id,
        }


def setup(bot: commands.Bot):
    """
    Compatible with extension loaders that either:
      - call setup(bot) normally (sync), or
      - call setup(bot) and await the result
    """
    setup_queue_commands(bot)
    return _AwaitableNoop()
