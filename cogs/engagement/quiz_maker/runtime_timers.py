# cogs/engagement/quiz_maker/runtime_timers.py
from __future__ import annotations

import asyncio
import logging
import time
from typing import Tuple

import discord

log = logging.getLogger(__name__)

SessionKey = Tuple[int, int]


async def run_question_timer(
    cog: "QuizMakerCog",
    session,
    message: discord.Message,
    question_index: int,
) -> None:
    """Periodically update the question embed with remaining time."""
    try:
        while True:
            await asyncio.sleep(1)

            # If we moved on or finished, stop updating
            if session.current_index != question_index or session.is_finished():
                break

            now = time.perf_counter()

            # Per question remaining time (active time on this question)
            per_remaining = None
            if session.question_timeout and session.current_question_started_at is not None:
                per_left = int(
                    session.question_timeout
                    - (now - session.current_question_started_at)
                )
                per_remaining = max(0, per_left)

            # Total quiz remaining based on cumulative active answering time
            total_remaining = None
            if session.total_timeout:
                used = sum(session.question_durations)
                if session.current_question_started_at is not None:
                    used += max(0.0, now - session.current_question_started_at)

                total_left = int(session.total_timeout - used)
                total_remaining = max(0, total_left)

            if per_remaining is None and total_remaining is None:
                break

            if not message.embeds:
                continue

            embed = message.embeds[0]

            timer_lines = []
            if per_remaining is not None and session.question_timeout:
                timer_lines.append(
                    f"Per question: **{per_remaining} s** remaining "
                    f"of **{session.question_timeout} s**."
                )
            if total_remaining is not None and session.total_timeout:
                timer_lines.append(
                    f"Total quiz: **{total_remaining} s** remaining "
                    f"of **{session.total_timeout} s**."
                )

            if not timer_lines:
                continue

            field_index = None
            for i, field in enumerate(embed.fields):
                if field.name == "⏱ Time":
                    field_index = i
                    break

            timer_value = "\n".join(timer_lines)
            if field_index is not None:
                embed.set_field_at(
                    index=field_index,
                    name="⏱ Time",
                    value=timer_value,
                    inline=False,
                )
            else:
                embed.add_field(
                    name="⏱ Time",
                    value=timer_value,
                    inline=False,
                )

            try:
                await message.edit(embed=embed)
            except Exception:
                log.exception("Failed to update quiz timer embed")
                break
    except asyncio.CancelledError:
        return
    except Exception:
        log.exception("Error in quiz question timer task")


async def watch_total_timeout(
    cog: "QuizMakerCog",
    session_key: SessionKey,
) -> None:
    """
    Watch the overall quiz time limit based on active answering time.

    Total limit is:
        total_timeout = question_timeout * total_questions

    but instead of wall clock, we count the same "time spent" that the
    summary uses so they cannot disagree.
    """
    warn_before = 15
    warned = False

    try:
        while True:
            await asyncio.sleep(1)

            session = cog.sessions.get(session_key)
            if session is None or session.is_finished():
                return

            total_limit = session.total_timeout
            if not total_limit or total_limit <= 0:
                return

            # Active time used so far
            used = sum(session.question_durations)
            if session.current_question_started_at is not None:
                used += max(0.0, time.perf_counter() - session.current_question_started_at)

            remaining = total_limit - used

            if remaining <= 0:
                channel = cog.bot.get_channel(session.channel_id)
                if channel is None:
                    return

                await channel.send(
                    f"⏰ Quiz time limit reached for <@{session.user_id}>. Ending the quiz."
                )
                await cog._send_summary(channel, session)
                return

            if remaining <= warn_before and not warned:
                channel = cog.bot.get_channel(session.channel_id)
                if channel is not None:
                    await channel.send(
                        f"⏰ Quiz time limit will be reached in {int(remaining)} seconds "
                        f"for <@{session.user_id}>."
                    )
                warned = True
    except asyncio.CancelledError:
        return
    except Exception:
        # If this blows up, do not kill the whole bot
        log.exception("Error in quiz total timer task")
