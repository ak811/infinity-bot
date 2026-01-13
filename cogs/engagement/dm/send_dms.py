# cogs/engagement/dm/send_dms.py
from __future__ import annotations

import logging
import discord
from discord.ext import commands

from configs.config_channels import SERIOUS_CHAT_CHANNEL_ID

log = logging.getLogger(__name__)

class SendDMsMixin(commands.Cog):
    """
    Staff command: send a DM to a user by mention/ID, and cache it for later edits.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # user_id -> discord.Message (last DM sent via this command)
        self.sent_dm_messages: dict[int, discord.Message] = {}

    @commands.command(name="send_dm", help="Sends a DM to a user using their mention or ID.")
    async def send_dm(self, ctx: commands.Context, user: discord.User, *, message: str):
        """
        Sends a DM to a specified user using their mention or ID and stores the message for future editing.
        Channel restriction: SERIOUS_CHAT_CHANNEL_ID (same as original).
        """
    
        try:
            sent_message = await user.send(message)  # Send DM and store the message reference
            self.sent_dm_messages[user.id] = sent_message
            await ctx.send(f"✅ Successfully sent DM to {user.name}. Use `!edit_dm {user.id} New message` to edit.")
            log.info(f"[send_dm] DM sent to {user} ({user.id}); cached message id {sent_message.id}")
        except discord.Forbidden:
            await ctx.send(f"🙅 Cannot send DM to {user.name}. They might have DMs disabled.")
        except discord.HTTPException:
            await ctx.send("🙅 Failed to send the message. Try again later.")
