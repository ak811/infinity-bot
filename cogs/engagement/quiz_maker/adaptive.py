# cogs/engagement/quiz_maker/adaptive.py
from __future__ import annotations

import logging
from typing import List, Callable, Awaitable, Optional, Tuple

from openai import AsyncOpenAI

from .question_builder import build_questions_from_text
from .quiz_session import QuizSession

log = logging.getLogger(__name__)

MAX_ADAPTIVE_BATCH = 5


async def maybe_generate_more_questions_for_session(
    client: AsyncOpenAI,
    session: QuizSession,
    status_callback: Optional[Callable[[str], Awaitable[None]]] = None,
) -> None:
    """
    For adaptive mode, generate additional batches of questions as needed.
    Ensures we try to reach the total number the user requested and avoid repeats.

    If status_callback is provided, it will be awaited with human readable updates.
    """
    if session.level != "adaptive":
        return
    if session.source_text is None:
        return

    # Already have enough questions for the target total
    if len(session.questions) >= session.total_questions:
        return

    # Only generate when we have exhausted the current batch
    if session.current_index < len(session.questions):
        return

    remaining = session.total_questions - len(session.questions)
    if remaining <= 0:
        return

    batch_size = min(MAX_ADAPTIVE_BATCH, remaining)
    next_level, level_change_message = choose_next_difficulty(session)

    if status_callback is not None and level_change_message:
        await status_callback(level_change_message)

    if status_callback is not None:
        await status_callback(
            f"🧠 Generating **{batch_size}** more `{next_level}` questions "
            f"for the adaptive quiz..."
        )

    existing_prompts: List[str] = [q.prompt for q in session.questions]

    try:
        new_questions = await build_questions_from_text(
            client,
            session.source_text,
            num_questions=batch_size,
            level=next_level,
            existing_questions=existing_prompts,
        )
    except Exception as exc:
        log.error(
            "Failed to generate more questions for adaptive quiz: %s",
            exc,
            exc_info=True,
        )
        if status_callback is not None:
            await status_callback(
                "❌ Failed to generate additional questions for the adaptive quiz."
            )
        return

    if not new_questions:
        if status_callback is not None:
            await status_callback(
                "⚠️ No additional questions could be generated for the adaptive quiz."
            )
        return

    session.questions.extend(new_questions)

    if status_callback is not None:
        await status_callback(
            f"✅ Added **{len(new_questions)}** `{next_level}` questions. "
            f"Continuing the quiz..."
        )


def choose_next_difficulty(session: QuizSession) -> Tuple[str, Optional[str]]:
    """
    Use recent accuracy and timing to pick the next difficulty level.

    Production oriented tweaks:
    - Look at a rolling window of recent questions
    - Add a cooldown so difficulty does not change every single question
    - Adjust only one step at a time between easy, medium and hard
    """
    levels = ["easy", "medium", "hard"]
    current = session.current_adaptive_level or "medium"
    if current not in levels:
        current = "medium"

    n = len(session.answers)
    if n == 0:
        return current, None

    # Cooldown: avoid flipping difficulty too frequently
    if session.last_level_change_at is not None:
        if n - session.last_level_change_at < 2:
            return current, None

    window_size = min(8, n)
    indices = list(range(n - window_size, n))

    correct_count = 0
    times: List[float] = []
    for i in indices:
        ans = session.answers[i] if i < len(session.answers) else None
        q = session.questions[i] if i < len(session.questions) else None
        if q is not None and ans is not None and ans == q.correct_index:
            correct_count += 1
        if i < len(session.question_durations):
            times.append(session.question_durations[i])

    if not indices:
        return current, None

    accuracy = correct_count / float(window_size)
    avg_time = sum(times) / len(times) if times else 0.0

    # Thresholds are intentionally asymmetric for hysteresis
    upgrade_accuracy = 0.75
    downgrade_accuracy = 0.45
    fast_threshold = 12.0
    slow_threshold = 18.0

    target = current
    if accuracy >= upgrade_accuracy and avg_time <= fast_threshold:
        target = "hard"
    elif accuracy <= downgrade_accuracy and avg_time >= slow_threshold:
        target = "easy"
    else:
        target = "medium"

    cur_idx = levels.index(current)
    tgt_idx = levels.index(target)

    if tgt_idx > cur_idx:
        new_idx = cur_idx + 1
    elif tgt_idx < cur_idx:
        new_idx = cur_idx - 1
    else:
        new_idx = cur_idx

    new_level = levels[new_idx]
    level_change_message: Optional[str] = None
    if new_level != current:
        session.last_level_change_at = n
        direction = "increased to" if levels.index(new_level) > levels.index(current) else "decreased to"
        level_change_message = (
            f"📈 Difficulty {direction} **{new_level.capitalize()}** based on your recent answers."
        )

    session.current_adaptive_level = new_level
    return new_level, level_change_message
