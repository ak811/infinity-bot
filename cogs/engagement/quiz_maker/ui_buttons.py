# cogs/engagement/quiz_maker/ui_buttons.py
from __future__ import annotations

from typing import Tuple

import discord

SessionKey = Tuple[int, int]


class QuizAnswerButton(discord.ui.Button):
    def __init__(
        self,
        label: str,
        choice_index: int,
        question_index: int,
        cog: "QuizMakerCog",
        session_key: SessionKey,
    ) -> None:
        super().__init__(style=discord.ButtonStyle.primary, label=label)
        self.choice_index = choice_index
        self.question_index = question_index
        self.cog = cog
        self.session_key = session_key

    async def callback(self, interaction: discord.Interaction) -> None:  # type: ignore[override]
        await interaction.response.defer(ephemeral=False)
        await self.cog.handle_answer(
            interaction,
            self.session_key,
            self.choice_index,
            self.question_index,
            view=self.view,
        )


class SkipQuestionButton(discord.ui.Button):
    def __init__(
        self,
        question_index: int,
        cog: "QuizMakerCog",
        session_key: SessionKey,
    ) -> None:
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Skip question",
            row=1,
        )
        self.question_index = question_index
        self.cog = cog
        self.session_key = session_key

    async def callback(self, interaction: discord.Interaction) -> None:  # type: ignore[override]
        await interaction.response.defer(ephemeral=False)
        await self.cog.handle_skip_question(
            interaction,
            self.session_key,
            self.question_index,
            view=self.view,
        )


class EndQuizButton(discord.ui.Button):
    def __init__(
        self,
        question_index: int,
        cog: "QuizMakerCog",
        session_key: SessionKey,
    ) -> None:
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="End quiz",
            row=1,
        )
        self.question_index = question_index
        self.cog = cog
        self.session_key = session_key

    async def callback(self, interaction: discord.Interaction) -> None:  # type: ignore[override]
        await self.cog.handle_end_quiz(
            interaction,
            self.session_key,
            self.question_index,
            view=self.view,
        )
