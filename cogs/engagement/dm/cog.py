# cogs/engagement/dm/cog.py
from __future__ import annotations

import logging
from discord.ext import commands

from .bot_dms import BotDMsMixin
from .send_dms import SendDMsMixin
from .edit_dms import EditDMsMixin

log = logging.getLogger(__name__)

class DMCog(BotDMsMixin, SendDMsMixin, EditDMsMixin, commands.Cog):
    """
    Composite Cog that:
      • Listens to user DMs and forwards them to a staff channel (BotDMsMixin)
      • Adds !send_dm for staff to DM users (SendDMsMixin)
      • Adds !edit_dm to edit the last sent DM (EditDMsMixin)
    """
    def __init__(self, bot: commands.Bot):
        # Call MRO chain so each mixin can init its state (sent_dm_messages, dm cache, etc.)
        super().__init__()
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(DMCog(bot))
