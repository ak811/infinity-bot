# cogs/engagement/quiz_maker/ui_summary_view.py
from __future__ import annotations

import logging

import discord

log = logging.getLogger(__name__)


class QuizSummaryView(discord.ui.View):
    """View attached to the summary embed with actions to replay or review."""

    def __init__(self, cog: "QuizMakerCog", session) -> None:
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
