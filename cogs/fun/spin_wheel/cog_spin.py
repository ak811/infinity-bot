from __future__ import annotations

import time
import logging
from typing import Dict

import discord
from discord.ext import commands

from .config_spin import (
    ENTRY_FEE_COINS,
    SPIN_COOLDOWN_SECONDS,
    EMOJI,
)
from .view_spin import SpinView

from cogs.economy.coin.service import update_coins, get_total_coins
from cogs.economy.orb.service import update_orbs
from cogs.economy.star.service import update_stars
from cogs.economy.diamond.service import update_diamonds

from configs.helper import send_as_webhook

# In-memory cooldown tracker {user_id: last_spin_unix_ts}
_spin_cooldowns: Dict[int, float] = {}


class SpinWheelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="spin", aliases=["sp"])
    async def spin_cmd(self, ctx: commands.Context):
        """Start a spin-the-wheel game."""
        uid = ctx.author.id

        # === Cooldown check (pre-flight UX). We'll re-check at click time as well. ===
        if SPIN_COOLDOWN_SECONDS > 0:
            last = _spin_cooldowns.get(uid, 0.0)
            now = time.time()
            if now - last < SPIN_COOLDOWN_SECONDS:
                rem = int(SPIN_COOLDOWN_SECONDS - (now - last))
                mins, secs = divmod(rem, 60)
                return await send_as_webhook(ctx, "spin", content=f"⏳ You can spin again in {mins}m {secs}s.")

        # === Balance check (pre-flight UX). We'll re-check + charge at click time. ===
        try:
            current = get_total_coins(uid)
        except Exception as e:
            logging.error(f"[spin] failed to get balance: {e}")
            return await ctx.send("🙅 Could not check your balance.")
        if current < ENTRY_FEE_COINS:
            return await ctx.send(f"Not enough coins. You need **{ENTRY_FEE_COINS} {EMOJI['coins']}**.")

        # === Award callback ===
        async def award_callback(user_id: int, totals: Dict[str, int]):
            """Apply the payout amounts to the user's balances."""
            for cur, amt in totals.items():
                if amt <= 0:
                    continue
                try:
                    if cur == "coins":
                        update_coins(user_id, amt, "Spin Reward")
                    elif cur == "orbs":
                        update_orbs(user_id, amt, "Spin Reward")
                    elif cur == "stars":
                        update_stars(user_id, amt, "Spin Reward")
                    elif cur == "diamonds":
                        update_diamonds(user_id, amt, "Spin Reward")
                except Exception as e:
                    logging.error(f"[spin] failed to award {amt} {cur} to {user_id}: {e}")

        # === Cooldown helpers ===
        def get_last_spin(user_id: int) -> float:
            return _spin_cooldowns.get(user_id, 0.0)

        def set_last_spin(user_id: int, ts: float) -> None:
            _spin_cooldowns[user_id] = ts

        # === Show rules embed ===
        rules = (
            f"• Entry Fee: **{ENTRY_FEE_COINS} {EMOJI['coins']}**\n"
            f"• Rewards: Coins {EMOJI['coins']}, Orbs {EMOJI['orbs']}, Stars {EMOJI['stars']}, Diamonds {EMOJI['diamonds']}\n"
        )
        embed = discord.Embed(
            title="🎡 Spin The Wheel",
            description=rules,
            color=discord.Color.blurple()
        )

        view = SpinView(
            author_id=uid,
            entry_fee=ENTRY_FEE_COINS,
            award_callback=award_callback,
            cooldown_seconds=SPIN_COOLDOWN_SECONDS,
            get_last_spin=get_last_spin,
            set_last_spin=set_last_spin,
            # FAST preset; tweak as you like
            speed_steps=0.4,   # fewer frames
            speed_time=0.4,    # shorter sleeps
        )
        sent = await send_as_webhook(ctx, "spin", embed=embed, view=view)
        view.message = sent


async def setup(bot: commands.Bot):
    await bot.add_cog(SpinWheelCog(bot))
