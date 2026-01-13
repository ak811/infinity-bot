# cogs/engagement/quiz_maker/runtime_actions.py
from __future__ import annotations

import logging
import time
from typing import Optional, Tuple

import discord

from .adaptive import maybe_generate_more_questions_for_session
from .runtime_questions import send_next_question, send_summary

log = logging.getLogger(__name__)

SessionKey = Tuple[int, int]


async def handle_answer(
    cog: "QuizMakerCog",
    interaction: discord.Interaction,
    session_key: SessionKey,
    choice_index: int,
    question_index: int,
    view: Optional[discord.ui.View] = None,
) -> None:
    session = cog.sessions.get(session_key)
    if session is None:
        await interaction.followup.send(
            "❌ This quiz is no longer active.",
            ephemeral=True,
        )
        return

    if not session.is_multiplayer and interaction.user.id != session.user_id:
        await interaction.followup.send(
            "⛔ This is not your quiz.",
            ephemeral=True,
        )
        return

    if question_index != session.current_index:
        await interaction.followup.send(
            "⌛ That question has already been answered or expired.",
            ephemeral=True,
        )
        return

    if view is not None:
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        try:
            if interaction.message:
                await interaction.message.edit(view=view)
        except Exception:
            log.exception("Failed to disable quiz buttons after answer")

    elapsed: Optional[float] = None
    if session.current_question_started_at is not None:
        elapsed = time.perf_counter() - session.current_question_started_at
        session.question_durations.append(elapsed)

    try:
        is_correct, question = session.answer(choice_index)
    except Exception:
        await interaction.followup.send(
            "❌ There was no question to answer.",
            ephemeral=True,
        )
        return

    correct_letter = chr(ord("A") + question.correct_index)
    your_letter = chr(ord("A") + choice_index)

    if is_correct:
        status_emoji = "✅"
        status_text = "Correct"
    else:
        status_emoji = "❌"
        status_text = "Incorrect"

    msg_lines = [
        f"{status_emoji} **{status_text}!**",
        "",
        f"🧠 Your choice: **{your_letter}**",
        f"✅ Correct answer: **{correct_letter}**",
        "",
        "🧾 **Explanation**",
        question.explanation or "No explanation provided.",
    ]

    if elapsed is not None:
        msg_lines.append(f"⏱ You answered in **{elapsed:.1f} seconds**.")

    msg_lines.append(
        f"📊 Current score: **{session.score} / {session.current_index}**"
    )

    await interaction.followup.send("\n".join(msg_lines))

    channel = interaction.channel
    if channel is None:
        return

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


async def handle_skip_question(
    cog: "QuizMakerCog",
    interaction: discord.Interaction,
    session_key: SessionKey,
    question_index: int,
    view: Optional[discord.ui.View] = None,
) -> None:
    session = cog.sessions.get(session_key)
    if session is None:
        await interaction.followup.send(
            "❌ This quiz is no longer active.",
            ephemeral=True,
        )
        return

    if not session.is_multiplayer and interaction.user.id != session.user_id:
        await interaction.followup.send(
            "⛔ This is not your quiz.",
            ephemeral=True,
        )
        return

    if question_index != session.current_index:
        await interaction.followup.send(
            "⌛ That question has already been answered or expired.",
            ephemeral=True,
        )
        return

    if view is not None:
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        try:
            if hasattr(view, "message") and view.message:
                await view.message.edit(view=view)
            elif interaction.message:
                await interaction.message.edit(view=view)
        except Exception:
            log.exception("Failed to disable quiz buttons on skip")

    question = session.current_question()
    if question is None:
        await interaction.followup.send(
            "❌ There was no question to skip.",
            ephemeral=True,
        )
        return

    elapsed = 0.0
    if session.current_question_started_at is not None:
        elapsed = time.perf_counter() - session.current_question_started_at

    session.question_durations.append(elapsed)
    session.answers.append(None)
    session.current_index += 1

    correct_letter = chr(ord("A") + question.correct_index)
    msg_lines = [
        f"⏭ **You skipped that question, <@{session.user_id}>**",
        "",
        f"✅ Correct answer: **{correct_letter}**",
        "",
        "🧾 **Explanation**",
        question.explanation or "No explanation provided.",
    ]
    if elapsed > 0:
        msg_lines.append(f"⏱ You used **{elapsed:.1f} seconds** before skipping.")

    msg_lines.append(
        f"📊 Current score: **{session.score} / {session.current_index}**"
    )

    await interaction.followup.send("\n".join(msg_lines))

    channel = interaction.channel or (
        view.message.channel if hasattr(view, "message") and view.message else None
    )
    if channel is None:
        return

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


async def handle_end_quiz(
    cog: "QuizMakerCog",
    interaction: discord.Interaction,
    session_key: SessionKey,
    question_index: int,
    view: Optional[discord.ui.View] = None,
) -> None:
    session = cog.sessions.get(session_key)
    if session is None:
        await interaction.response.send_message(
            "❌ This quiz is no longer active.",
            ephemeral=True,
        )
        return

    if not session.is_multiplayer and interaction.user.id != session.user_id:
        await interaction.response.send_message(
            "⛔ This is not your quiz.",
            ephemeral=True,
        )
        return

    if question_index != session.current_index:
        await interaction.response.send_message(
            "⌛ That question has already been answered or expired.",
            ephemeral=True,
        )
        return

    if view is not None:
        for child in view.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        try:
            if hasattr(view, "message") and view.message:
                await view.message.edit(view=view)
            elif interaction.message:
                await interaction.message.edit(view=view)
        except Exception:
            log.exception("Failed to disable quiz buttons on end quiz")

    session.target_total_questions = session.current_index

    channel = interaction.channel or (
        view.message.channel if hasattr(view, "message") and view.message else None
    )
    if channel is None:
        await interaction.response.send_message(
            "❌ I could not find a channel to send the summary in.",
            ephemeral=True,
        )
        return

    try:
        await interaction.response.send_message(
            "🛑 You ended the quiz. Showing summary...",
            ephemeral=True,
        )
    except discord.InteractionResponded:
        pass

    await send_summary(cog, channel, session)
