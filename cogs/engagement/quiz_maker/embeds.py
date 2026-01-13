# cogs/engagement/quiz_maker/embeds.py
from __future__ import annotations

from typing import Any, Dict, List

import discord

from .quiz_session import Question, QuizSession
from .summary import SummaryStats


def build_question_embed(session: QuizSession, question: Question) -> discord.Embed:
    idx = session.current_index + 1
    total = session.total_questions

    # Determine effective difficulty for this question
    raw_level = getattr(question, "difficulty", session.level) or session.level or "medium"
    level_key = str(raw_level).lower()
    if level_key not in {"easy", "medium", "hard"}:
        level_key = "medium"

    difficulty_label = level_key.capitalize()

    # Color code by difficulty
    if level_key == "easy":
        color = discord.Color.green()
    elif level_key == "hard":
        color = discord.Color.red()
    else:
        color = discord.Color.blurple()

    mode_label = "Adaptive" if session.level == "adaptive" else session.level.capitalize()

    title_suffix = f"• {difficulty_label}"
    embed = discord.Embed(
        title=f"🧩 Question {idx} of {total} {title_suffix}",
        description=f"**{question.prompt}**",
        color=color,
    )

    letters = ["A", "B", "C", "D", "E"]
    lines: List[str] = []
    for i, choice in enumerate(question.choices):
        label = letters[i] if i < len(letters) else str(i + 1)
        lines.append(f"**{label}.** {choice}")
    embed.add_field(name="Options", value="\n".join(lines), inline=False)

    if total > 0:
        bar_length = 10
        filled = int(bar_length * idx / total)
        if filled < 1:
            filled = 1
        if filled > bar_length:
            filled = bar_length
        bar = "▰" * filled + "▱" * (bar_length - filled)
        embed.add_field(
            name="Progress",
            value=f"{bar}  {idx}/{total}",
            inline=False,
        )

    # Time limits, if any
    time_lines: List[str] = []
    if session.question_timeout:
        time_lines.append(
            f"Per question limit: **{session.question_timeout} seconds**."
        )
    if session.total_timeout:
        time_lines.append(
            f"Total quiz limit: **{session.total_timeout} seconds**."
        )
    if time_lines:
        embed.add_field(
            name="⏱ Time",
            value="\n".join(time_lines),
            inline=False,
        )

    question_level_label = difficulty_label

    footer_parts = [
        f"Mode: {mode_label}",
        f"Question level: {question_level_label}",
        "Tap a button below to answer.",
    ]
    embed.set_footer(text=" • ".join(footer_parts))
    return embed


def build_quiz_stats_embed(
    user: discord.abc.User,
    stats: Dict[str, Any],
) -> discord.Embed:
    embed = discord.Embed(
        title=f"📊 Quiz stats for {user.display_name}",
        color=discord.Color.green(),
    )
    embed.add_field(
        name="Quizzes played",
        value=str(stats["quizzes_played"]),
        inline=True,
    )
    embed.add_field(
        name="Total score",
        value=f"{stats['total_score']} / {stats['total_questions']}",
        inline=True,
    )
    embed.add_field(
        name="Average score",
        value=f"{stats['avg_percent']:.1f}%",
        inline=True,
    )
    embed.add_field(
        name="Best score",
        value=f"{stats['best_score']} ({stats['best_percent']:.1f}%)",
        inline=True,
    )
    fastest = stats.get("overall_fastest_time")
    embed.add_field(
        name="Fastest question",
        value=(f"{fastest:.1f} seconds" if fastest is not None else "Not recorded"),
        inline=True,
    )
    return embed


def build_leaderboard_embed(
    guild: discord.Guild,
    board: List[Dict[str, Any]],
) -> discord.Embed:
    embed = discord.Embed(
        title="🏆 Quiz leaderboard",
        color=discord.Color.gold(),
    )
    lines: List[str] = []
    for idx, entry in enumerate(board, start=1):
        member = guild.get_member(entry["user_id"])
        name = member.display_name if member else f"<@{entry['user_id']}>"
        lines.append(
            f"{idx}. **{name}** - {entry['avg_percent']:.1f}% avg "
            f"over {entry['quizzes_played']} quizzes"
        )
    embed.description = "\n".join(lines)
    return embed


def build_review_embed(session: QuizSession, index: int) -> discord.Embed:
    question = session.questions[index]
    letters = ["A", "B", "C", "D", "E"]

    user_answer_index = session.answers[index] if index < len(session.answers) else None
    correct_index = question.correct_index

    correct_letter = (
        letters[correct_index] if correct_index < len(letters) else str(correct_index + 1)
    )

    if user_answer_index is None:
        your_letter = "No answer"
        result_text = "Skipped or timed out"
    else:
        your_letter = (
            letters[user_answer_index]
            if user_answer_index < len(letters)
            else str(user_answer_index + 1)
        )
        result_text = "Correct" if user_answer_index == correct_index else "Incorrect"

    embed = discord.Embed(
        title=f"Question {index + 1}",
        description=question.prompt,
        color=discord.Color.blurple(),
    )
    options_lines: List[str] = []
    for i, choice in enumerate(question.choices):
        label = letters[i] if i < len(letters) else str(i + 1)
        options_lines.append(f"**{label}.** {choice}")
    embed.add_field(name="Options", value="\n".join(options_lines), inline=False)

    embed.add_field(name="Your answer", value=your_letter, inline=True)
    embed.add_field(name="Correct answer", value=correct_letter, inline=True)
    embed.add_field(name="Result", value=result_text, inline=True)
    embed.add_field(
        name="Explanation",
        value=question.explanation or "No explanation provided.",
        inline=False,
    )

    question_level_label = (
        getattr(question, "difficulty", session.level) or "medium"
    ).capitalize()
    embed.set_footer(text=f"Question level: {question_level_label}")

    return embed


def build_summary_embed(session: QuizSession, stats: SummaryStats) -> discord.Embed:
    """Build a clean summary embed with score and timing stats."""
    percent = stats.percent
    if percent >= 90:
        color = discord.Color.gold()
        emoji = "🏅"
    elif percent >= 80:
        color = discord.Color.green()
        emoji = "🔥"
    elif percent >= 50:
        color = discord.Color.blurple()
        emoji = "📝"
    else:
        color = discord.Color.red()
        emoji = "😬"

    title = f"{emoji} Quiz summary"
    description = f"Results for <@{session.user_id}>"

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
    )

    embed.add_field(
        name="Score",
        value=f"{stats.score} / {stats.total_questions} ({stats.percent}%)",
        inline=True,
    )
    embed.add_field(
        name="Mode",
        value=session.level.capitalize(),
        inline=True,
    )

    questions_answered = len(session.answers)
    embed.add_field(
        name="Questions answered",
        value=str(questions_answered),
        inline=True,
    )

    if stats.total_time > 0:
        embed.add_field(
            name="Total time",
            value=f"{stats.total_time:.1f} seconds",
            inline=True,
        )
        embed.add_field(
            name="Average per question",
            value=f"{stats.average_time:.1f} seconds",
            inline=True,
        )

        if stats.fastest_time is not None and stats.fastest_index is not None:
            embed.add_field(
                name="Fastest question",
                value=f"Q{stats.fastest_index} in {stats.fastest_time:.1f} seconds",
                inline=False,
            )
        if stats.slowest_time is not None and stats.slowest_index is not None:
            embed.add_field(
                name="Slowest question",
                value=f"Q{stats.slowest_index} in {stats.slowest_time:.1f} seconds",
                inline=False,
            )

    embed.set_footer(
        text="Use the buttons below to play again or get a detailed review."
    )
    return embed
