# cogs/leaderboard/embed_update.py
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

from configs.config_logging import logging
from configs.config_channels import LEADERBOARD_CHANNEL_ID
from configs.config_files import ACTIVITY_DATA_FILE

from cogs.economy.xp.service import update_xp

from cogs.stats.leaderboard.rows import (
    compute_coins_row,
    coins_sort_key,
    format_coins_row,
)
from cogs.stats.leaderboard.manager import refresh_generic_leaderboard


class LeaderboardUpdater(commands.Cog):
    """
    Keeps the main leaderboard embed fresh:
      • Ticks live VC seconds for users currently in VC (per minute).
      • Rebuilds and updates the single persistent leaderboard message.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Ensure the join_times & processed set exist (used by voice tracking and this loop)
        if not hasattr(self.bot, "join_times"):
            self.bot.join_times: dict[str, datetime] = {}
        if not hasattr(self.bot, "processed_in_leaderboard"):
            self.bot.processed_in_leaderboard: set[str] = set()

        # start the loop when the cog loads
        self.update_main_leaderboard.start()

    def cog_unload(self):
        self.update_main_leaderboard.cancel()

    @tasks.loop(minutes=1, reconnect=True)
    async def update_main_leaderboard(self):
        """Every minute: tick VC XP for active users and refresh the leaderboard."""
        try:
            now = datetime.now(timezone.utc)

            # Tick VC seconds for everyone currently in VC
            for user_id, join_time in list(self.bot.join_times.items()):
                # Defensive: ensure join_time is datetime
                if not isinstance(join_time, datetime):
                    continue
                duration = int((now - join_time).total_seconds())
                if duration > 0:
                    update_xp(user_id, duration, activity_type="vc")
                    self.bot.join_times[user_id] = now  # advance their tick anchor
                    self.bot.processed_in_leaderboard.add(user_id)

            # Build/update the persistent leaderboard message
            message, pages = await refresh_generic_leaderboard(
                bot=self.bot,
                title="🏆 Leaderboard: Top Players",
                message_id_key="leaderboard",                # key stored in SHOP_IDS_FILE
                channel_id=int(LEADERBOARD_CHANNEL_ID),
                compute_fn=compute_coins_row,
                sort_key_fn=coins_sort_key,
                format_fn=format_coins_row,
                file=ACTIVITY_DATA_FILE,
                items_per_page=10,
                post_to_channel=True,                        # edit the persistent message
            )

            # Add rotating footer hint (only on the first page we post)
            if message and pages:
                embed = pages[0]
                embed.set_footer(text="⏱️ Next refresh in ~1 minute.")
                try:
                    await message.edit(embed=embed)
                except discord.HTTPException:
                    pass

        except Exception as e:
            logging.exception(f"[LeaderboardUpdater] update loop failed: {e}")

    @update_main_leaderboard.before_loop
    async def _before_loop(self):
        await self.bot.wait_until_ready()
        logging.info("[LeaderboardUpdater] Starting loop…")


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaderboardUpdater(bot))
