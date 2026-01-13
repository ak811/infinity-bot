# cogs/engagement/quiz_maker/runtime_start.py
from __future__ import annotations

import logging
import time
from typing import Tuple

import discord

from .question_builder import build_questions_from_text
from .quiz_session import QuizSession
from .runtime_questions import send_next_question
from .runtime_timers import watch_total_timeout

log = logging.getLogger(__name__)

SessionKey = Tuple[int, int]


async def start_quiz_from_setup(
    cog: "QuizMakerCog",
    interaction: discord.Interaction,
    setup_view,
) -> None:
    channel = interaction.channel
    if channel is None:
        await interaction.followup.send(
            "❌ No channel found to send questions in.",
            ephemeral=True,
        )
        return

    user = interaction.user
    key: SessionKey = (channel.id, user.id)
    if key in cog.sessions:
        await interaction.followup.send(
            "⚠️ You already have an active quiz in this channel. "
            "Finish or cancel it before starting another one.",
            ephemeral=True,
        )
        return

    text = setup_view.source_text
    filename = setup_view.filename
    num_questions_requested = setup_view.selected_questions
    difficulty_mode = setup_view.selected_level
    timed = setup_view.timed

    # Per question timeout
    question_timeout = 30 if timed else 0
    # Total timeout is "time per question * requested number of questions"
    total_timeout = (
        question_timeout * num_questions_requested
        if timed and question_timeout > 0
        else 0
    )

    await channel.send(
        f"🧠 Preparing up to **{num_questions_requested}** `{difficulty_mode}` questions "
        f"from `{filename}`."
    )
    if timed:
        await channel.send(
            f"⏱ Timed quiz: **{question_timeout} seconds per question**, "
            f"total time limit **{total_timeout} seconds**."
        )
    else:
        await channel.send("⏱ This quiz is untimed.")

    try:
        if difficulty_mode == "adaptive":
            initial_batch = min(5, num_questions_requested)
            questions = await build_questions_from_text(
                cog.client,
                text,
                num_questions=initial_batch,
                level="medium",
            )
        else:
            questions = await build_questions_from_text(
                cog.client,
                text,
                num_questions=num_questions_requested,
                level=difficulty_mode,
            )
    except Exception as exc:
        log.error("Question generation failed: %s", exc, exc_info=True)
        await channel.send(
            "❌ Failed to generate questions from that file."
        )
        await interaction.followup.send(
            "❌ I could not start the quiz due to a generation error.",
            ephemeral=True,
        )
        return

    if not questions:
        await channel.send(
            "❌ I could not generate any valid questions from that file."
        )
        await interaction.followup.send(
            "❌ I could not start the quiz because no questions were generated.",
            ephemeral=True,
        )
        return

    # For non adaptive mode, if the model returned fewer questions than requested,
    # run the quiz with the actual count so the score denominator matches reality.
    if difficulty_mode != "adaptive" and len(questions) < num_questions_requested:
        await channel.send(
            f"⚠️ I was only able to generate **{len(questions)}** questions "
            f"from that file, so this quiz will use **{len(questions)}** "
            f"instead of **{num_questions_requested}**."
        )

    session = QuizSession(
        user_id=user.id,
        channel_id=channel.id,
        questions=questions,
        level=difficulty_mode,
        guild_id=interaction.guild_id,
        is_multiplayer=False,
    )
    session.started_at = time.perf_counter()
    # For adaptive mode we track the requested total separately
    if difficulty_mode == "adaptive":
        session.target_total_questions = num_questions_requested
        session.current_adaptive_level = "medium"
        session.last_level_change_at = None
    else:
        # Non adaptive quizzes use the number of generated questions as the total
        session.target_total_questions = None

    session.source_text = text
    session.question_timeout = question_timeout or None
    # This is the total active answering time budget
    session.total_timeout = total_timeout or None

    cog.sessions[key] = session

    # Start total timer watcher if timed
    if total_timeout > 0:
        cog.bot.loop.create_task(
            watch_total_timeout(cog, key)
        )

    await send_next_question(cog, channel, session)
    await channel.send(
        f"📚 Quiz started in this channel for {user.mention} "
        f"(mode: **{difficulty_mode.capitalize()}**, "
        f"{session.total_questions} questions). Good luck."
    )
    await interaction.followup.send(
        "✅ Your quiz has started in this channel.",
        ephemeral=True,
    )



async def restart_quiz_from_summary(
    cog: "QuizMakerCog",
    interaction: discord.Interaction,
    previous_session: QuizSession,
) -> None:
    channel = cog.bot.get_channel(previous_session.channel_id) or interaction.channel
    if channel is None:
        await interaction.followup.send(
            "❌ I could not find the original quiz channel.",
            ephemeral=True,
        )
        return

    key: SessionKey = (previous_session.channel_id, previous_session.user_id)
    if key in cog.sessions:
        await interaction.followup.send(
            "⚠️ You already have an active quiz in that channel.",
            ephemeral=True,
        )
        return

    if previous_session.source_text is None:
        await interaction.followup.send(
            "❌ I do not have the original quiz source text to recreate this quiz.",
            ephemeral=True,
        )
        return

    num_questions_requested = previous_session.total_questions
    difficulty_mode = previous_session.level
    question_timeout = previous_session.question_timeout or 0
    total_timeout = question_timeout * num_questions_requested if question_timeout > 0 else 0

    await channel.send(
        f"🔁 Starting a new quiz for <@{previous_session.user_id}> "
        f"with **{num_questions_requested}** `{difficulty_mode}` questions."
    )
    if question_timeout or total_timeout:
        details = []
        if question_timeout:
            details.append(f"{question_timeout} s per question")
        if total_timeout:
            details.append(f"{total_timeout} s total limit")
        await channel.send("⏱ Timed quiz: " + ", ".join(details) + ".")
    else:
        await channel.send("⏱ This quiz is untimed.")

    try:
        if difficulty_mode == "adaptive":
            initial_batch = min(5, num_questions_requested)
            questions = await build_questions_from_text(
                cog.client,
                previous_session.source_text,
                num_questions=initial_batch,
                level="medium",
            )
        else:
            questions = await build_questions_from_text(
                cog.client,
                previous_session.source_text,
                num_questions=num_questions_requested,
                level=difficulty_mode,
            )
    except Exception as exc:
        log.error("Question generation failed on restart: %s", exc, exc_info=True)
        await channel.send("❌ Failed to generate questions for the new quiz.")
        await interaction.followup.send(
            "❌ I could not restart the quiz due to a generation error.",
            ephemeral=True,
        )
        return

    if not questions:
        await channel.send("❌ I could not generate any valid questions for the new quiz.")
        await interaction.followup.send(
            "❌ I could not restart the quiz because no questions were generated.",
            ephemeral=True,
        )
        return

    if difficulty_mode != "adaptive" and len(questions) < num_questions_requested:
        await channel.send(
            f"⚠️ I was only able to generate **{len(questions)}** questions "
            f"for this quiz, so it will use **{len(questions)}** "
            f"instead of **{num_questions_requested}**."
        )

    session = QuizSession(
        user_id=previous_session.user_id,
        channel_id=channel.id,
        questions=questions,
        level=difficulty_mode,
        guild_id=previous_session.guild_id,
        is_multiplayer=False,
    )
    session.started_at = time.perf_counter()

    if difficulty_mode == "adaptive":
        session.target_total_questions = num_questions_requested
        session.current_adaptive_level = "medium"
        session.last_level_change_at = None
    else:
        session.target_total_questions = None

    session.source_text = previous_session.source_text
    session.question_timeout = question_timeout or None
    session.total_timeout = total_timeout or None

    cog.sessions[key] = session

    if total_timeout > 0:
        cog.bot.loop.create_task(
            watch_total_timeout(cog, key)
        )

    await send_next_question(cog, channel, session)
    await interaction.followup.send(
        "✅ New quiz started with the same settings.",
        ephemeral=True,
    )
