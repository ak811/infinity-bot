# cogs/engagement/quiz_maker/ui.py
from __future__ import annotations

import logging
from typing import Optional, Tuple

import discord

from .quiz_session import QuizSession

log = logging.getLogger(__name__)

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

        # Extra controls for each question
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


class QuizSetupView(discord.ui.View):
    """Interactive setup view for selecting quiz options before generation."""

    def __init__(
        self,
        cog: "QuizMakerCog",
        user_id: int,
        source_text: str,
        filename: str,
    ) -> None:
        super().__init__(timeout=300)
        self.cog = cog
        self.user_id = user_id
        self.source_text = source_text
        self.filename = filename
        self.selected_level: str = "medium"
        self.selected_questions: int = 5
        self.timed: bool = False
        self.message: Optional[discord.Message] = None

    async def _ensure_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "⛔ You are not configuring this quiz.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.select(
        placeholder="Select difficulty",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="Easy", value="easy", description="Basic questions"),
            discord.SelectOption(label="Medium", value="medium", description="Intermediate questions"),
            discord.SelectOption(label="Hard", value="hard", description="Challenging questions"),
            discord.SelectOption(label="Adaptive", value="adaptive", description="Automatically adjusts difficulty"),
        ],
    )
    async def difficulty_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ) -> None:
        if not await self._ensure_owner(interaction):
            return
        self.selected_level = select.values[0]
        await interaction.response.send_message(
            f"🎚 Difficulty set to **{self.selected_level.capitalize()}**.",
            ephemeral=True,
        )

    @discord.ui.select(
        placeholder="Number of questions",
        min_values=1,
        max_values=1,
        options=[
            discord.SelectOption(label="5 questions", value="5"),
            discord.SelectOption(label="10 questions", value="10"),
            discord.SelectOption(label="15 questions", value="15"),
            discord.SelectOption(label="20 questions", value="20"),
            discord.SelectOption(label="30 questions", value="30"),
        ],
    )
    async def question_count_select(
        self,
        interaction: discord.Interaction,
        select: discord.ui.Select,
    ) -> None:
        if not await self._ensure_owner(interaction):
            return
        try:
            self.selected_questions = int(select.values[0])
        except ValueError:
            self.selected_questions = 5
        await interaction.response.send_message(
            f"🔢 Question count set to **{self.selected_questions}**.",
            ephemeral=True,
        )

    @discord.ui.button(
        label="Timed: OFF",
        style=discord.ButtonStyle.secondary,
    )
    async def toggle_timed(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self._ensure_owner(interaction):
            return
        self.timed = not self.timed
        button.label = "Timed: ON" if self.timed else "Timed: OFF"
        button.style = (
            discord.ButtonStyle.success if self.timed else discord.ButtonStyle.secondary
        )
        try:
            await interaction.response.edit_message(view=self)
        except Exception:
            log.exception("Failed to update timed toggle button state")

    @discord.ui.button(
        label="Start quiz",
        style=discord.ButtonStyle.success,
    )
    async def start_quiz(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self._ensure_owner(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        # Disable controls to avoid duplicate starts
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        try:
            if interaction.message:
                await interaction.message.edit(view=self)
        except Exception:
            log.exception("Failed to disable setup view after start")

        await self.cog.start_quiz_from_setup(interaction, self)

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            log.exception("Failed to disable setup view on timeout")


class QuizSummaryView(discord.ui.View):
    """View attached to the summary embed with actions to replay or review."""

    def __init__(self, cog: "QuizMakerCog", session: QuizSession) -> None:
        super().__init__(timeout=300)
        self.cog = cog
        self.session = session

    async def _ensure_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.session.user_id:
            await interaction.response.send_message(
                "⛔ This quiz summary is not for you.",
                ephemeral=True,
            )
            return False
        return True

    @discord.ui.button(
        label="Play again with same settings",
        style=discord.ButtonStyle.success,
    )
    async def play_again(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self._ensure_owner(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        # Disable the play again button to avoid spamming
        button.disabled = True
        try:
            if interaction.message:
                await interaction.message.edit(view=self)
        except Exception:
            log.exception("Failed to disable play again button")

        await self.cog.restart_quiz_from_summary(interaction, self.session)

    @discord.ui.button(
        label="DM me a detailed review",
        style=discord.ButtonStyle.secondary,
    )
    async def dm_review(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ) -> None:
        if not await self._ensure_owner(interaction):
            return

        await interaction.response.defer(ephemeral=True)

        success = await self.cog._send_review_dm(interaction.user, self.session)
        if not success:
            await interaction.followup.send(
                "❌ I could not send you a DM. Check your privacy settings.",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            "📬 I sent you a DM with your quiz review.",
            ephemeral=True,
        )

    async def on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        try:
            pass
        except Exception:
            log.exception("Error cleaning up summary view on timeout")
