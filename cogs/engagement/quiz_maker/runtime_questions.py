# cogs/engagement/quiz_maker/runtime_questions.py
from __future__ import annotations

import logging
import time
from typing import Tuple

import discord

from .adaptive import maybe_generate_more_questions_for_session
from .embeds import (
    build_question_embed,
    build_review_embed,
    build_summary_embed,
)
from .summary import compute_summary_stats
from .stats import QuizResult
from .ui import QuizView, QuizSummaryView
from .runtime_timers import run_question_timer

log = logging.getLogger(__name__)

SessionKey = Tuple[int, int]


async def send_next_question(
    cog: "QuizMakerCog",
    channel: discord.abc.Messageable,
    session,
) -> None:
    question = session.current_question()

    if question is None and session.level == "adaptive":
        async def status_callback(msg: str) -> None:
            await channel.send(msg)

        await maybe_generate_more_questions_for_session(
            cog.client,
            session,
            status_callback=status_callback,
        )
        question = session.current_question()

    if question is None:
        await send_summary(cog, channel, session)
        return

    session.current_question_started_at = time.perf_counter()

    key: SessionKey = (session.channel_id, session.user_id)
    view = QuizView(
        cog=cog,
        session_key=key,
        question_index=session.current_index,
        num_choices=len(question.choices),
        question_timeout=session.question_timeout,
    )
    embed = build_question_embed(session, question)
    msg = await channel.send(
        content=f"<@{session.user_id}>",
        embed=embed,
        view=view,
    )
    view.message = msg

    if session.question_timeout or session.total_timeout:
        cog.bot.loop.create_task(
            run_question_timer(cog, session, msg, session.current_index)
        )


async def send_summary(
    cog: "QuizMakerCog",
    channel: discord.abc.Messageable,
    session,
) -> None:
    key: SessionKey = (session.channel_id, session.user_id)
    cog.sessions.pop(key, None)

    summary_stats = compute_summary_stats(session)
    embed = build_summary_embed(session, summary_stats)
    view = QuizSummaryView(cog=cog, session=session)
    await channel.send(embed=embed, view=view)

    try:
        result = QuizResult(
            user_id=session.user_id,
            guild_id=session.guild_id,
            channel_id=session.channel_id,
            score=session.score,
            total_questions=summary_stats.total_questions,
            percent=float(summary_stats.percent),
            difficulty_mode=session.level,
            total_time=summary_stats.total_time,
            average_time=summary_stats.average_time,
            fastest_time=summary_stats.fastest_time,
            slowest_time=summary_stats.slowest_time,
            timestamp=time.time(),
        )
        cog.stats_store.add_result(result)
    except Exception:
        log.exception("Failed to record quiz stats")


async def handle_question_timeout(
    cog: "QuizMakerCog",
    session_key: SessionKey,
    question_index: int,
    view: QuizView,
) -> None:
    session = cog.sessions.get(session_key)
    if session is None:
        return

    if question_index != session.current_index:
        return

    question = session.current_question()
    if question is None:
        return

    elapsed = 0.0
    if session.current_question_started_at is not None:
        elapsed = time.perf_counter() - session.current_question_started_at

    session.question_durations.append(elapsed)
    session.answers.append(None)
    session.current_index += 1

    for child in view.children:
        if isinstance(child, discord.ui.Button):
            child.disabled = True
    try:
        if view.message:
            await view.message.edit(view=view)
    except Exception:
        log.exception("Failed to disable quiz buttons on timeout")

    correct_letter = chr(ord("A") + question.correct_index)
    msg_lines = [
        f"⌛ **Time is up for that question, <@{session.user_id}>**",
        "",
        f"✅ Correct answer: **{correct_letter}**",
        "",
        "🧾 **Explanation**",
        question.explanation or "No explanation provided.",
    ]
    if elapsed > 0:
        msg_lines.append(f"⏱ You used **{elapsed:.1f} seconds**.")

    msg_lines.append(
        f"📊 Current score: **{session.score} / {session.current_index}**"
    )

    channel = view.message.channel if view.message else None
    if channel is None:
        return

    await channel.send("\n".join(msg_lines))

    async def status_callback(msg: str) -> None:
        await channel.send(msg)

    await maybe_generate_more_questions_for_session(
        cog.client,
        session,
        status_callback=status_callback,
    )

    if session.is_finished():
        await send_summary(cog, channel, session)
    else:
        await send_next_question(cog, channel, session)


async def send_review_dm(
    cog: "QuizMakerCog",
    user: discord.abc.User,
    session,
) -> bool:
    """DM the user a detailed quiz review.

    Uses the same scoring denominator as the summary so the numbers line up.
    """
    try:
        dm = await user.create_dm()
    except Exception:
        log.exception("Failed to create DM for quiz review")
        return False

    stats = compute_summary_stats(session)

    await dm.send(
        f"📚 Review for your last quiz "
        f"(mode: **{session.level.capitalize()}**, "
        f"score: **{stats.score}/{stats.total_questions}**)."
    )

    # Only send details for questions that actually counted
    limit = min(stats.total_questions, len(session.questions))
    for idx in range(limit):
        embed = build_review_embed(session, idx)
        await dm.send(embed=embed)

    return True
