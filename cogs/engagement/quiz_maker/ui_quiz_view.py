# cogs/engagement/quiz_maker/ui_quiz_view.py
from __future__ import annotations

import logging
from typing import Optional, Tuple

import discord

from .ui_buttons import QuizAnswerButton, SkipQuestionButton, EndQuizButton

log = logging.getLogger(__name__)

SessionKey = Tuple[int, int]


class QuizView(discord.ui.View):
    def __init__(
        self,
        cog: "QuizMakerCog",
        session_key: SessionKey,
        question_index: int,
        num_choices: int,
        question_timeout: Optional[int] = None,
    ) -> None:
        super().__init__(timeout=question_timeout or None)
        self.cog = cog
        self.session_key = session_key
        self.question_index = question_index
        self.message: Optional[discord.Message] = None

        labels = ["A", "B", "C", "D", "E"][:num_choices]
        for idx, label in enumerate(labels):
            self.add_item(
                QuizAnswerButton(
                    label=label,
                    choice_index=idx,
                    question_index=question_index,
                    cog=cog,
                    session_key=session_key,
                )
            )

        self.add_item(
            SkipQuestionButton(
                question_index=question_index,
                cog=cog,
                session_key=session_key,
            )
        )
        self.add_item(
            EndQuizButton(
                question_index=question_index,
                cog=cog,
                session_key=session_key,
            )
        )

    async def on_timeout(self) -> None:
        try:
            await self.cog.handle_question_timeout(
                self.session_key,
                self.question_index,
                self,
            )
        except Exception:
            log.exception("Error handling quiz question timeout")
