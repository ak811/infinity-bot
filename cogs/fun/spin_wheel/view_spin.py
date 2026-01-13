"""
Discord UI view for Spin-the-Wheel (fast, deterministic, bold center).
Supports multi-currency combo payouts and clean, no-jump animation.
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Callable, Awaitable, Dict, Optional

import discord
from discord import Embed

from .config_spin import (
    EMOJI,
    ANIMATION_MIN_DELAY,
    ANIMATION_MAX_DELAY,
    MAX_CHAINED_SPINS,
    WHEEL,
    ROTATION_LOOPS,
    EXTRA_TICKS_AFTER_LOOPS,
)
from .wheel_engine import spin_once, Outcome

# Economy functions used for charging balance at click time
from cogs.economy.coin.service import get_total_coins
from cogs.economy.orb.service import get_total_orbs
from cogs.economy.diamond.service import get_total_diamonds
from cogs.economy.star.service import get_total_stars

# Callback type for awarding payouts (coins/orbs/stars/diamonds dict)
AwardCallback = Callable[[int, Dict[str, int]], Awaitable[None]]

# Cooldown helper types
GetLastSpin = Callable[[int], float]
SetLastSpin = Callable[[int, float], None]  # setter takes (user_id, ts)


class SpinView(discord.ui.View):
    def __init__(
        self,
        author_id: int,
        entry_fee: int,
        award_callback: AwardCallback,
        cooldown_seconds: int,
        get_last_spin: GetLastSpin,
        set_last_spin: SetLastSpin,
        rng: Optional[random.Random] = None,
        max_spins: int = MAX_CHAINED_SPINS,
        window_size: int = 15,          # must be odd
        speed_steps: float = 0.5,      # scale number of frames (lower = fewer frames)
        speed_time: float = 0.5,       # scale per-frame sleep time (lower = faster)
    ):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.entry_fee = entry_fee
        self.award_callback = award_callback
        self.cooldown_seconds = cooldown_seconds
        self.get_last_spin = get_last_spin
        self.set_last_spin = set_last_spin
        self.rng = rng or random
        self.message: Optional[discord.Message] = None

        # State
        self.entry_charged = False
        self.spins_done = 0
        self.max_spins = max_spins
        self.is_animating = False
        self.resolved = False
        self.multiplier = 1

        # Speed scaling
        self.speed_steps = max(0.1, float(speed_steps))
        self.speed_time = max(0.1, float(speed_time))

        # Window geometry
        if window_size < 3 or window_size % 2 == 0:
            raise ValueError("window_size must be an odd integer >= 3")
        self.window_size = window_size
        self.center_index = window_size // 2

    async def on_timeout(self):
        # Disable button on timeout
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

    # ---------- Rendering helpers ----------

    def _render_window_from_indices(self, idx_window: list[int], selected_index: int) -> str:
        """
        Render a window of entries by index (stable even with duplicate labels).
        The selected slot (center) is bold and pointed.
        """
        lines: list[str] = []
        for i, idx in enumerate(idx_window):
            label = WHEEL[idx].label
            dist = abs(i - selected_index)
            indent = dist  # farther -> more indent to suggest depth
            pointer = ">" if i == selected_index else ""
            bullet = "🔹" if i == selected_index else "🔸"
            if i == selected_index:
                label = f"**{label}**"
            lines.append(f"{' ' * indent}{pointer}{bullet} {label}")
        return "```\n" + "\n".join(lines) + "\n```"

    async def _ensure_base_message(self, inter: discord.Interaction, embed: Embed) -> Optional[discord.Message]:
        # Prefer the existing message we can edit repeatedly
        msg: Optional[discord.Message] = self.message or inter.message
        if not msg:
            try:
                if inter.channel is not None:
                    msg = await inter.channel.send(embed=embed, view=None)
                    self.message = msg
            except Exception as e:
                logging.warning(f"[SpinView] failed to create base message: {e}")
                try:
                    await inter.followup.send(embed=embed, ephemeral=True)
                except Exception:
                    pass
        return msg

    async def _animate_and_reveal(self, msg: Optional[discord.Message], user_display: str, target_index: int, header: str):
        """
        Deterministic rotation with no jumps:
        - Traverse in natural modular order (0..n-1) from a random start.
        - Choose total steps so the last frame centers on target_index.
        - Monotonic ease-out: per-frame delay never decreases.
        """
        n = max(1, len(WHEEL))
        center = self.center_index
        start = self.rng.randrange(n)

        # Steps: loops + extra ticks, scaled by speed knob
        base_steps = max(0, int(ROTATION_LOOPS)) * n + max(0, int(EXTRA_TICKS_AFTER_LOOPS))
        base_steps = max(1, int(base_steps * self.speed_steps))

        # Align so that final frame centers on target_index
        extra_to_align = (target_index - start - (base_steps - 1)) % n
        total_steps = base_steps + extra_to_align

        embed = Embed(
            title="🎡 Spin the Wheel",
            description=f"{header}\n\nGood luck! ✨",
            color=discord.Color.blurple()
        )

        last_delay = 0.0
        for tick in range(total_steps):
            cur = (start + tick) % n  # index at wheel center this frame
            first = (cur - center) % n
            idx_window = [(first + i) % n for i in range(self.window_size)]

            embed.description = f"Spinning for **{user_display}**...\n" + self._render_window_from_indices(
                idx_window, selected_index=center
            )
            if msg:
                try:
                    await msg.edit(embed=embed)
                except Exception:
                    pass

            # Monotonic ease-out timing
            if total_steps <= 1:
                delay = ANIMATION_MIN_DELAY
            else:
                t = tick / (total_steps - 1)
                delay = ANIMATION_MIN_DELAY + (ANIMATION_MAX_DELAY - ANIMATION_MIN_DELAY) * (t ** 1.3)

            delay *= self.speed_time
            if delay < last_delay:
                delay = last_delay  # enforce non-decreasing delay
            last_delay = delay

            await asyncio.sleep(delay)

        # Brief settle pause already centered on target
        await asyncio.sleep(0.45 * self.speed_time)

    def _totals_from_outcome(self, outcome: Outcome) -> Dict[str, int]:
        totals = {"coins": 0, "orbs": 0, "stars": 0, "diamonds": 0}
        if outcome.kind == "payout":
            if outcome.payouts:
                for cur, amt in outcome.payouts.items():
                    if cur in totals and amt > 0:
                        totals[cur] += int(amt)
            elif outcome.currency is not None and outcome.amount is not None:  # allow amount = 0
                totals[outcome.currency] += int(outcome.amount)

        # Apply any active stacked multiplier
        if self.multiplier > 1:
            for k in totals:
                totals[k] *= self.multiplier
        return totals

    @discord.ui.button(label="🎡 Spin Now", style=discord.ButtonStyle.success, custom_id="spin_wheel_go")
    async def spin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Ownership & state checks
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This spin isn’t yours! 🙅", ephemeral=True)
        if self.resolved:
            return await interaction.response.send_message("This wheel is already finished. 💨", ephemeral=True)
        if self.is_animating:
            return await interaction.response.send_message("Hang on, the wheel is still spinning…", ephemeral=True)

        # Cooldown (pre-charge)
        if (not self.entry_charged) and self.cooldown_seconds > 0:
            last = self.get_last_spin(self.author_id)
            now = time.time()
            if now - last < self.cooldown_seconds:
                rem = int(self.cooldown_seconds - (now - last))
                mins, secs = divmod(rem, 60)
                return await interaction.response.send_message(
                    f"⏳ You can spin again in {mins}m {secs}s.", ephemeral=True
                )

        # First click: charge entry fee and stamp cooldown
        if not self.entry_charged:
            try:
                balance = get_total_coins(self.author_id)
            except Exception as e:
                logging.error(f"[SpinView] failed to get balance: {e}")
                return await interaction.response.send_message("🙅 Could not check your balance.", ephemeral=True)

            if balance < self.entry_fee:
                return await interaction.response.send_message(
                    f"Not enough coins. You need **{self.entry_fee} {EMOJI['coins']}**.", ephemeral=True
                )

            try:
                update_coins(self.author_id, -self.entry_fee, "Spin Entry Fee")
                self.entry_charged = True
            except Exception as e:
                logging.error(f"[SpinView] entry fee charge failed: {e}")
                return await interaction.response.send_message("🙅 Could not deduct entry fee.", ephemeral=True)

            if self.cooldown_seconds > 0:
                self.set_last_spin(self.author_id, time.time())

        # Disable button during animation and acknowledge
        self.is_animating = True
        button.disabled = True
        try:
            await interaction.response.edit_message(view=self)
        except discord.InteractionResponded:
            pass
        except Exception:
            try:
                await interaction.response.defer()
            except Exception:
                pass

        user = interaction.user
        header = f"Spinning for **{user.display_name}**..." + (f"  (⚡ ×{self.multiplier} active)" if self.multiplier > 1 else "")
        base_embed = Embed(
            title="🎡 Spin the Wheel",
            description=f"{header}\n\nGood luck! ✨",
            color=discord.Color.blurple()
        )
        msg = await self._ensure_base_message(interaction, base_embed)

        # Account this attempt
        self.spins_done += 1

        # Roll outcome (equal probability per slot)
        outcome = spin_once(rng=self.rng)

        # If at/over cap and the result isn't a payout, force resolution to a payout
        if self.spins_done >= self.max_spins and outcome.kind != "payout":
            attempts = 0
            while outcome.kind != "payout" and attempts < 20:
                outcome = spin_once(rng=self.rng)
                attempts += 1

        # Animate deterministically to the outcome index
        target_index = int(outcome.entry_index or 0)
        await self._animate_and_reveal(msg, user.display_name, target_index, header)

        # Handle specials
        if outcome.kind == "multiplier":
            self.multiplier *= 2  # stack it
            self.is_animating = False
            button.disabled = False
            if msg:
                try:
                    embed = Embed(
                        title="⚡ Multiplier Activated",
                        description=(
                            f"{user.display_name}, your **next spin** prize will be multiplied by **×{self.multiplier}**.\n"
                            "Click **Spin Now** to continue."
                        ),
                        color=discord.Color.gold()
                    )
                    await msg.edit(embed=embed, view=self)
                except Exception:
                    pass
            return

        if outcome.kind == "respin":
            self.is_animating = False
            button.disabled = False
            if msg:
                try:
                    embed = Embed(
                        title="🔁 Free Re-Spin",
                        description=f"{user.display_name}, you got a **Free Spin Token**. Click **Spin Now** to use it.",
                        color=discord.Color.gold()
                    )
                    await msg.edit(embed=embed, view=self)
                except Exception:
                    pass
            return

        # ---- Payout path ----
        self.resolved = True
        self.is_animating = False
        button.disabled = True  # finished; disable controls

        totals = self._totals_from_outcome(outcome)
        self.multiplier = 1  # consume/reset stacked multiplier

        # Apply payout via callback
        try:
            await self.award_callback(user.id, totals)
        except Exception as e:
            logging.error(f"[SpinView] award_callback error: {e}")

        # Fetch balances for display
        try:
            coins_bal = get_total_coins(user.id)
        except Exception:
            coins_bal = 0

        try:
            orbs_bal = get_total_orbs(user.id)
            stars_bal = get_total_stars(user.id)
            diamonds_bal = get_total_diamonds(user.id)
        except Exception:
            orbs_bal = stars_bal = diamonds_bal = 0

        # Figure out multiplier and base prize values
        mult = self.multiplier
        self.multiplier = 1  # reset after using

        base_totals = self._totals_from_outcome(Outcome(
            kind=outcome.kind,
            label=outcome.label,
            currency=outcome.currency,
            amount=outcome.amount,
            payouts=outcome.payouts,
            entry_index=outcome.entry_index
        ))
        # Remove multiplier from base_totals calculation
        if mult > 1:
            for k in base_totals:
                base_totals[k] = int(base_totals[k] / mult)

        totals = self._totals_from_outcome(outcome)  # already multiplied

        # Build prize text (handles single or multi-currency)
        def format_prize_line():
            parts = []
            for cur, base_amt in base_totals.items():
                if base_amt > 0:
                    final_amt = totals[cur]
                    if mult > 1:
                        parts.append(f"{EMOJI[cur]} {base_amt} × {mult} = {final_amt} {cur.capitalize()}")
                    else:
                        parts.append(f"{EMOJI[cur]} {final_amt} {cur.capitalize()}")
            return " + ".join(parts) if parts else outcome.label

        prize_line = f"🎉 You won **{format_prize_line()}**"

        # Final embed
        final_embed = Embed(
            title=f"🎡 Spin Result for {user.display_name}",
            description=(
                f"{prize_line}\n\n"
                f"💰 Balance: {coins_bal} {EMOJI['coins']} | "
                f"{orbs_bal} {EMOJI['orbs']} | "
                f"{stars_bal} {EMOJI['stars']} | "
                f"{diamonds_bal} {EMOJI['diamonds']}"
            ),
            color=discord.Color.green()
        )

        if msg:
            try:
                await msg.edit(embed=final_embed, view=None)
            except Exception:
                pass
        else:
            try:
                await interaction.followup.send(embed=final_embed, ephemeral=True)
            except Exception:
                pass
