# cogs/tree/cog.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from configs.config_channels import GROW_A_TREE_CHANNEL_ID, LOGS_CHANNEL_ID
from configs.helper import send_as_webhook

# Use in-package pings helpers
from cogs.networking.pings.filters import select_eligible_users, shuffled_mentions
from cogs.networking.pings.storage import load_ping_toggles

from .storage import (
    load_last_orb_receiver, save_last_orb_receiver,
    load_last_ping_timestamp, save_last_ping_timestamp,
    load_ping_roles,
)
from .logic import extract_watering_user_id, extract_target_unix, award_orb_and_announce

# ID of the third-party tree bot that posts the embeds
GROW_A_TREE_BOT_ID = 972637072991068220


class TreeCog(commands.Cog):
    """Monitors the Grow-a-Tree channel: rewards waterers and pings subscribers before the timer elapses."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # persistent state
        self.last_orb_receiver: int | None = load_last_orb_receiver(None)
        self.last_ping_timestamp: int | None = load_last_ping_timestamp(None)

        # Kick off the monitor loop
        self.monitor_loop.start()

    async def cog_unload(self):
        self.monitor_loop.cancel()

    @tasks.loop(seconds=30.0)
    async def monitor_loop(self):
        try:
            channel = self.bot.get_channel(GROW_A_TREE_CHANNEL_ID)
            rewards_channel = self.bot.get_channel(LOGS_CHANNEL_ID)

            if not isinstance(channel, discord.TextChannel):
                logging.warning("[GrowTree] GROW_A_TREE_CHANNEL_ID not found or not a TextChannel.")
                return
            if not rewards_channel:
                logging.warning("[GrowTree] LOGS_CHANNEL_ID not found.")
                return

            logging.info(f"[GrowTree] Tick. last_ping_ts={self.last_ping_timestamp}, last_orb_receiver={self.last_orb_receiver}")

            # find the most recent *watering/timer* embed from the tree bot (ignore leaderboards)
            latest_embed_msg: discord.Message | None = None
            description = ""
            
            async for msg in channel.history(limit=150):
                if msg.author.id != GROW_A_TREE_BOT_ID or not msg.embeds:
                    continue
            
                desc = msg.embeds[0].description or ""
                # pick embeds that contain the watering line or a Discord relative timestamp
                if ("watering the tree" in desc.lower()) or ("<t:" in desc):
                    latest_embed_msg = msg
                    description = desc
                    break
            
            if not latest_embed_msg:
                logging.info("[GrowTree] No watering/timer embed found this tick.")
                return
            
            embed = latest_embed_msg.embeds[0]
            
            logging.info(f"[GrowTree] Using embed msg_id={latest_embed_msg.id} title={embed.title!r}")
            logging.info(f"[GrowTree] Embed desc sample={description[:250]!r}")

            # 1) Award orb if watering detected (avoid dupes)
            user_id = extract_watering_user_id(description)
            if user_id:
                if user_id != self.last_orb_receiver:
                    user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                    if user:
                        logging.info(f"[GrowTree] Awarding orb to {user_id}")
                        await award_orb_and_announce(channel, user)
                        self.last_orb_receiver = user_id
                        save_last_orb_receiver(self.last_orb_receiver)
                    else:
                        logging.warning(f"[GrowTree] Could not fetch user {user_id}")
                else:
                    logging.info("[GrowTree] Same user as last reward; skipping orb.")

            # 2) Timer & ping logic
            target_ts = extract_target_unix(description)
            if target_ts:
                now_ts = int(datetime.now(tz=timezone.utc).timestamp())

                # send only once per cycle (5 min tolerance)
                already_pinged = (
                    self.last_ping_timestamp is not None
                    and abs(self.last_ping_timestamp - target_ts) <= 300
                )

                # Trigger the ping when we're within ~10s of the target (or past it)
                should_ping_now = not already_pinged and (now_ts >= target_ts - 10)

                if should_ping_now:
                    logging.info(f"[GrowTree] Ready to ping for ts={target_ts} (now={now_ts})")

                    # 1) Gather candidates
                    ping_roles = load_ping_roles()  # {"GROW_TREE_PING_1": [ids...], ...}
                    ping_ids = ping_roles.get("GROW_TREE_PING_1", [])
                    logging.info(f"[GrowTree] Subscribers={len(ping_ids)}")

                    # 2) Load personal toggles (0=off, 1=on, 2=online-only) and filter by presence + toggles
                    ping_toggles = load_ping_toggles()
                    eligible_ping_ids, debug_rows = select_eligible_users(
                        guild=channel.guild,
                        candidate_ids=ping_ids,
                        ping_toggles=ping_toggles,
                    )
                    logging.info(f"[GrowTree] Eligible={len(eligible_ping_ids)} (sample={debug_rows[:5]})")

                    generic_reminder = (
                        f"🌳✨ The **{channel.guild.name}** Tree is ready to be watered again — let's make it grow tall and strong!\n"
                        f"💧 Who will be the next hero?"
                    )

                    if not ping_ids or not eligible_ping_ids:
                        # No subscribers or no one eligible → send reminder without mentions
                        await send_as_webhook(channel, "grow_a_tree_reminder", content=generic_reminder)
                        self._mark_ping_sent(target_ts)
                        logging.info("[GrowTree] Reminder sent (no subscribers/eligible).")
                    else:
                        shuffled_ids, mentions = shuffled_mentions(eligible_ping_ids)
                        if len(shuffled_ids) <= 30:
                            logging.debug(f"[GrowTree] Mention order: {shuffled_ids}")
                        else:
                            logging.debug(f"[GrowTree] Mention sample: {shuffled_ids[:30]} (+{len(shuffled_ids)-30} more)")

                        await send_as_webhook(
                            channel,
                            "grow_a_tree_reminder",
                            content=generic_reminder + "\n" + mentions,
                        )
                        self._mark_ping_sent(target_ts)
                        logging.info(f"[GrowTree] Ping with {len(shuffled_ids)} mentions sent.")

            # otherwise: no timer in the embed this tick

        except Exception as e:
            logging.error(f"[GrowTree] Error in monitor loop: {e}", exc_info=True)

    def _mark_ping_sent(self, target_ts: int) -> None:
        self.last_ping_timestamp = target_ts
        save_last_ping_timestamp(target_ts)
        logging.info(f"[GrowTree] Saved ping timestamp: {target_ts}")

    @monitor_loop.before_loop
    async def before_monitor_loop(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(TreeCog(bot))
