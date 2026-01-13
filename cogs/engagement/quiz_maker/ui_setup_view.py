# cogs/engagement/quiz_maker/ui_setup_view.py
from __future__ import annotations

import logging
from typing import Optional

import discord

log = logging.getLogger(__name__)


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
