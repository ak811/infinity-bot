# cogs/server/emojis/checks.py
from __future__ import annotations
import discord
from discord.ext import commands
from .errors import GuildOnlyError, IntentsMissingError

def require_guild(ctx: commands.Context) -> discord.Guild:
    if not ctx.guild:
        raise GuildOnlyError()
    return ctx.guild

def ensure_intents(bot: commands.Bot) -> None:
    if not getattr(bot.intents, "emojis_and_stickers", False):
        raise IntentsMissingError()

def rate_limited_guild(calls: int = 1, per: int = 5):
    return commands.cooldown(calls, per, commands.BucketType.guild)
