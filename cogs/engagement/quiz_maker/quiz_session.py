# cogs/engagement/quiz_maker/quiz_session.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class Question:
    """Represents a single multiple choice question."""
    prompt: str
    choices: List[str]
    correct_index: int
    explanation: str
    # Per question difficulty label: "easy", "medium", "hard"
    difficulty: str = "medium"


@dataclass
class QuizSession:
    """
    Tracks quiz progress for a quiz in a single channel.

    Supports:
    - Single user mode (default)
    - Adaptive difficulty (using accuracy and timing)
    - Persistent timing and answer data for stats and review
    """
    user_id: int
    channel_id: int
    questions: List[Question]

    current_index: int = 0
    score: int = 0

    # Quiz difficulty mode: "easy", "medium", "hard", "adaptive"
    level: str = "medium"

    # Optional guild id
    guild_id: Optional[int] = None

    # Flags for possible future multi user mode
    is_multiplayer: bool = False

    # Timing data
    question_durations: List[float] = field(default_factory=list)
    started_at: float | None = None
    current_question_started_at: float | None = None

    # Adaptive mode metadata
    target_total_questions: Optional[int] = None
    current_adaptive_level: str = "medium"
    source_text: Optional[str] = None
    question_timeout: Optional[int] = None
    total_timeout: Optional[int] = None

    # Tracks when the last difficulty level change happened (by question index)
    last_level_change_at: Optional[int] = None

    # Per question answers (index into choices, or None if skipped / timed out)
    answers: List[Optional[int]] = field(default_factory=list)

    # For future multi user scoring
    player_scores: Dict[int, int] = field(default_factory=dict)

    def current_question(self) -> Optional[Question]:
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def answer(self, choice_index: int) -> Tuple[bool, Question]:
        """
        Apply an answer for the current question and advance index.

        Returns (is_correct, question).
        """
        question = self.current_question()
        if question is None:
            raise ValueError("No current question in session")

        is_correct = choice_index == question.correct_index
        if is_correct:
            self.score += 1

        # Record the chosen answer for review
        self.answers.append(choice_index)

        self.current_index += 1
        return is_correct, question

    @property
    def total_questions(self) -> int:
        """
        Target total questions for this quiz.

        For non adaptive mode this is just len(self.questions).
        For adaptive mode this is the requested total, which may be larger
        than the number of questions generated so far.
        """
        if self.target_total_questions is not None:
            return self.target_total_questions
        return len(self.questions)

    def is_finished(self) -> bool:
        """
        Returns True when the quiz has reached the requested number of questions,
        regardless of how many batches were generated.
        """
        target = self.target_total_questions or len(self.questions)
        return self.current_index >= target
