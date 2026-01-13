# cogs/engagement/quiz_maker/summary.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .quiz_session import QuizSession


@dataclass
class SummaryStats:
    score: int
    total_questions: int
    percent: int
    total_time: float
    average_time: float
    fastest_time: Optional[float]
    slowest_time: Optional[float]
    fastest_index: Optional[int]
    slowest_index: Optional[int]
    per_question_times: List[float]


def compute_summary_stats(session: QuizSession) -> SummaryStats:
    """
    Compute summary stats based on the questions that actually ran
    (answered, skipped or timed out), not the originally requested count.
    """
    score = session.score

    # Number of questions that actually completed in some way
    played = max(
        session.current_index,
        len(session.answers),
        len(session.question_durations),
    )

    # Fallback to the configured total if for some reason nothing ran
    total = played or session.total_questions
    percent = int(score * 100 / total) if total else 0

    durations = list(session.question_durations)
    total_time = sum(durations) if durations else 0.0
    average_time = total_time / len(durations) if durations else 0.0

    fastest_time: Optional[float] = None
    slowest_time: Optional[float] = None
    fastest_index: Optional[int] = None
    slowest_index: Optional[int] = None

    if durations:
        fastest_time = min(durations)
        slowest_time = max(durations)
        fastest_index = durations.index(fastest_time) + 1
        slowest_index = durations.index(slowest_time) + 1

    return SummaryStats(
        score=score,
        total_questions=total,
        percent=percent,
        total_time=total_time,
        average_time=average_time,
        fastest_time=fastest_time,
        slowest_time=slowest_time,
        fastest_index=fastest_index,
        slowest_index=slowest_index,
        per_question_times=durations,
    )


def build_summary_message(session: QuizSession, stats: SummaryStats) -> str:
    score = stats.score
    total = stats.total_questions
    percent = stats.percent

    if percent >= 90:
        emoji = "🏅"
    elif percent >= 80:
        emoji = "🔥"
    elif percent >= 50:
        emoji = "📝"
    else:
        emoji = "😬"

    lines: List[str] = [
        f"{emoji} **Quiz finished for <@{session.user_id}>**",
        "",
        f"🏁 **Final score:** **{score} / {total}** (`{percent}%`)",
        f"🎯 **Mode:** {session.level.capitalize()}",
    ]

    durations = stats.per_question_times
    if durations:
        lines.append("")
        lines.append("⏱ **Timing stats**")
        lines.append(f"- Total time: **{stats.total_time:.1f} seconds**")
        lines.append(f"- Average per question: **{stats.average_time:.1f} seconds**")

        if stats.fastest_time is not None and stats.fastest_index is not None:
            lines.append(
                f"- Fastest question: **Q{stats.fastest_index}** "
                f"in **{stats.fastest_time:.1f} seconds**"
            )
        if stats.slowest_time is not None and stats.slowest_index is not None:
            lines.append(
                f"- Slowest question: **Q{stats.slowest_index}** "
                f"in **{stats.slowest_time:.1f} seconds**"
            )

        per_q = ", ".join(
            f"Q{i + 1}: {d:.1f}s" for i, d in enumerate(durations)
        )
        lines.append(f"- Per question: {per_q}")

    return "\n".join(lines)
