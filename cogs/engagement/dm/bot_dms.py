# cogs/engagement/dm/bot_dms.py
from __future__ import annotations

import logging
import discord
from discord.ext import commands
from configs.config_channels import SERIOUS_CHAT_CHANNEL_ID

log = logging.getLogger(__name__)

class BotDMsMixin(commands.Cog):
    """
    Listens for user DMs and forwards them to a staff channel.
    Provides a one-time auto-ack per user per runtime.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # in case parent Cog defines __init__
        # runtime cache: user_id -> True once we've replied in this process
        self._user_dm_cache: set[int] = set()

    @commands.Cog.listener("on_message")
    async def _on_message_forward_dms(self, message: discord.Message):
        # Only DMs, not from bots
        if not isinstance(message.channel, discord.DMChannel):
            return
        if message.author.bot:
            return

        # Resolve staff forward channel
        forward_channel = (
            self.bot.get_channel(int(SERIOUS_CHAT_CHANNEL_ID))
            or await self._maybe_fetch_text_channel(int(SERIOUS_CHAT_CHANNEL_ID))
        )

        # Acknowledge to user
        try:
            if message.author.id not in self._user_dm_cache:
                self._user_dm_cache.add(message.author.id)
                await message.channel.send("👋 Hey there! Thanks for reaching out! 😊")
            else:
                await message.channel.send(
                    "⏳ Please wait while our staff gets back to you. Someone will reply shortly! 🧑‍💻"
                )
        except Exception:
            log.exception("[DM] Failed to send acknowledgement")

        # Forward the message to staff channel
        if isinstance(forward_channel, discord.TextChannel):
            try:
                embed = discord.Embed(
                    title="📩 New DM Received!",
                    description=(
                        f"**From:** {message.author.mention} ({message.author})\n\n"
                        f"**💬 Message:** {message.content or '*<no text>*'}"
                    ),
                    color=discord.Color.blurple(),
                )
                embed.set_footer(text=f"🆔 User ID: {message.author.id}")

                files = []
                try:
                    for a in message.attachments:
                        files.append(await a.to_file())
                except Exception:
                    files = []

                await forward_channel.send(embed=embed, files=files)
            except Exception:
                log.exception("[DM] Failed to forward DM to staff channel")
        else:
            log.warning("[DM] SERIOUS_CHAT_CHANNEL_ID not found or not a text channel")

    async def _maybe_fetch_text_channel(self, channel_id: int) -> discord.abc.GuildChannel | None:
        try:
            ch = await self.bot.fetch_channel(channel_id)
            return ch
        except Exception:
            return None
