# cogs/stats/logging/reactions/cog.py
from __future__ import annotations

import discord
from discord.ext import commands
from .add import upsert_reaction_log, _extract_message_preview
from .remove import emoji_key_from_payload
from configs.config_logging import logging
from configs.helper import delete_webhook_message


class ReactionsLoggingCog(commands.Cog):
    """
    Batched reaction logging (webhook or normal message fallback):
      - One log per (guild_id, channel_id, message_id, user_id)
      - On add/remove: edit that single log to reflect the full emoji set
      - When the set becomes empty: delete the log message
      - Includes a short preview of the original message (content + first embed bits)
        kept **inside the embed description** only.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # key: (guild_id, channel_id, message_id, user_id)
        # record: {
        #   "token": tuple[int, int | None, int] | None,  # (log_channel_id, webhook_id_or_none, message_id)
        #   "donor_id": int,
        #   "recipient_id": int,
        #   "jump_url": str,
        #   "channel_id": int,
        #   "emojis": dict[str, tuple[str, str]],  # key -> (icon, name)
        #   "preview": str,
        # }
        self._groups: dict[tuple[int, int, int, int], dict] = {}

    def _gkey(self, payload: discord.RawReactionActionEvent) -> tuple[int, int, int, int]:
        return (
            payload.guild_id or 0,
            payload.channel_id,
            payload.message_id,
            payload.user_id,
        )

    async def _ensure_group_loaded(self, payload: discord.RawReactionActionEvent) -> dict | None:
        if payload.guild_id is None:
            return None
        try:
            donor = self.bot.get_user(payload.user_id) or await self.bot.fetch_user(payload.user_id)
            if getattr(donor, "bot", False):
                return None

            channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
            if not isinstance(channel, (discord.TextChannel, discord.Thread)):
                return None

            message = await channel.fetch_message(payload.message_id)
            gkey = self._gkey(payload)
            rec = self._groups.get(gkey)
            if rec is None:
                rec = {
                    "token": None,
                    "donor_id": donor.id,
                    "recipient_id": message.author.id,
                    "jump_url": message.jump_url,
                    "channel_id": message.channel.id,
                    "emojis": {},
                    "preview": _extract_message_preview(message),  # embed-only
                }
                self._groups[gkey] = rec
            return rec
        except Exception as e:
            logging.warning(f"[ReactionLog] _ensure_group_loaded failed: {e}")
            return None

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        rec = await self._ensure_group_loaded(payload)
        if rec is None:
            return

        ekey = emoji_key_from_payload(payload)
        rec["emojis"][ekey] = (str(payload.emoji), payload.emoji.name or "emoji")

        try:
            donor = self.bot.get_user(rec["donor_id"]) or await self.bot.fetch_user(rec["donor_id"])
            token = await upsert_reaction_log(
                self.bot,
                donor=donor,
                recipient_id=rec["recipient_id"],
                jump_url=rec["jump_url"],
                channel_id=rec["channel_id"],
                emoji_items=list(rec["emojis"].values()),
                existing_token=rec["token"],
                message_preview=rec.get("preview"),  # embed-only
            )
            if token is not None:
                rec["token"] = token
        except Exception as e:
            logging.warning(f"[ReactionLog] upsert on add failed: {e}")

    @commands.Cog.listener()  # <-- fixed: removed extra ')'
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        gkey = self._gkey(payload)
        rec = self._groups.get(gkey)
        if rec is None:
            return

        ekey = emoji_key_from_payload(payload)
        rec["emojis"].pop(ekey, None)

        if not rec["emojis"]:
            token = rec.get("token")
            if token:
                ch_id, wh_id, msg_id = token
                try:
                    ok = await delete_webhook_message(self.bot, ch_id, wh_id, msg_id)
                    if not ok:
                        logging.warning("[ReactionLog] Webhook log deletion reported failure.")
                except Exception as e:
                    logging.warning(f"[ReactionLog] Exception while deleting webhook log: {e}")
            self._groups.pop(gkey, None)
            return

        try:
            donor = self.bot.get_user(rec["donor_id"]) or await self.bot.fetch_user(rec["donor_id"])
            token = await upsert_reaction_log(
                self.bot,
                donor=donor,
                recipient_id=rec["recipient_id"],
                jump_url=rec["jump_url"],
                channel_id=rec["channel_id"],
                emoji_items=list(rec["emojis"].values()),
                existing_token=rec["token"],
                message_preview=rec.get("preview"),  # embed-only
            )
            if token is not None:
                rec["token"] = token
        except Exception as e:
            logging.warning(f"[ReactionLog] upsert on remove failed: {e}")
