# cogs/close_circle/cog.py
from __future__ import annotations

import logging
import discord
from discord.ext import commands

from configs.config_general import BOT_GUILD_ID
from .storage import load_close_circle_data, save_close_circle_data
from .update import update_proximity, update_reply, update_mentions, update_voice_proximity
from . import cc as cc_cmd
from . import bff as bff_cmd
from . import ncc as ncc_cmd
from . import nbff as nbff_cmd

class CloseCircleCog(commands.Cog):
    """Tracks interactions to surface close connections, BFFs, NCC, and NBFF."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)
        load_close_circle_data()

    # --- listeners ------------------------------------------------------------

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return
        if message.guild.id != int(BOT_GUILD_ID):
            return
        # update in-process scoring
        update_proximity(message.author, message.channel.id)
        update_reply(message)
        update_mentions(message)

    @commands.Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # We only need reaction details to augment proximity when reading from a message object.
        # This cog expects external systems to call update_reactions_proximity(reaction, user) when appropriate,
        # or you can wire an on_reaction_add listener here if you prefer full coverage.
        pass

    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update_listener(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.guild is None or member.bot:
            return
        if member.guild.id != int(BOT_GUILD_ID):
            return
        update_voice_proximity(member, before, after)

    def cog_unload(self):
        try:
            save_close_circle_data()
        except Exception:
            self.log.error("[close_circle] Failed to save data on unload", exc_info=True)

    # --- prefix commands ------------------------------------------------------

    @commands.command(name="cc")
    async def cmd_cc(self, ctx: commands.Context, member: discord.Member | None = None):
        await cc_cmd.cc(ctx, member)

    @commands.command(name="bff")
    async def cmd_bff(self, ctx: commands.Context):
        await bff_cmd.bff(ctx)

    @commands.command(name="ncc")
    async def cmd_ncc(self, ctx: commands.Context, member: discord.Member | None = None):
        await ncc_cmd.ncc(ctx, member)

    @commands.command(name="nbff")
    async def cmd_nbff(self, ctx: commands.Context):
        await nbff_cmd.nbff(ctx)

async def setup(bot: commands.Bot):
    await bot.add_cog(CloseCircleCog(bot))
