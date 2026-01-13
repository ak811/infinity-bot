# cogs/engagement/dm/edit_dms.py
from __future__ import annotations

import logging
import discord
from discord.ext import commands

from configs.config_channels import BOT_PLAYGROUND_CHANNEL_ID
from configs.config_general import AUTHORIZED_USER_ID

log = logging.getLogger(__name__)

def is_admin(ctx: commands.Context) -> bool:
    return ctx.author.id == AUTHORIZED_USER_ID

class EditDMsMixin(commands.Cog):
    """
    Staff command: edit the last DM previously sent (via send_dm) to a given user ID.
    """

    @commands.command(name="sudo_edit_dm", help="Edits the last DM sent to a user using their ID.")
    async def sudo_edit_dm(self, ctx: commands.Context, user_id: int, *, new_message: str):
        """
        Edits the last DM sent to a specified user using their user ID.
        Only messages sent via `!send_dm` can be edited.
        Channel restriction: BOT_PLAYGROUND_CHANNEL_ID (same as original).
        """
        if not is_admin(ctx):
            await ctx.send("🙅 You do not have permission to edit DMs.")
            return

        user = self.bot.get_user(user_id)
        if not user:
            await ctx.send(f"🙅 No user found with ID {user_id}. Make sure you provided the correct ID.")
            return

        # The cache is owned by SendDMsMixin; DMCog composes both mixins, so it's on self.
        cache = getattr(self, "sent_dm_messages", {})
        if user.id in cache:
            try:
                sent_message: discord.Message = cache[user.id]
                await sent_message.edit(content=new_message)
                log.info(f"[edit_dm] Edited DM message {sent_message.id} for user {user.id}")
                await ctx.send(f"✅ Successfully edited DM for {user.name}.")
            except discord.HTTPException:
                await ctx.send("🙅 Failed to edit the message. Try again later.")
        else:
            await ctx.send(
                f"🙅 No previous DM found for {user.name}. You can only edit messages sent via `!send_dm`."
            )
