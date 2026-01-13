# cogs/leaderboard/base_view.py
from __future__ import annotations

import logging
import discord


class BaseLeaderboardView(discord.ui.View):
    """
    Tiny paginator for a list[discord.Embed].
    `locate_callback(user)` should return a page index or None.
    """
    def __init__(self, pages: list[discord.Embed], locate_callback):
        super().__init__(timeout=None)
        self.pages = pages or [discord.Embed(description="No data.")]
        self.locate_callback = locate_callback
        self.current_page = 0

    async def _safe_edit(self, interaction: discord.Interaction, embed: discord.Embed):
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except (discord.errors.InteractionResponded, discord.errors.NotFound):
            await interaction.message.edit(embed=embed, view=self)

    async def update_message(self, interaction: discord.Interaction):
        embed = self.pages[self.current_page]
        await self._safe_edit(interaction, embed)
        logging.info(f"Leaderboard page -> {self.current_page}")

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary, custom_id="previous_page")
    async def previous_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.current_page = (self.current_page - 1) % len(self.pages)
        await self.update_message(interaction)

    @discord.ui.button(label="📍", style=discord.ButtonStyle.success, custom_id="locate_user")
    async def locate_user_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        found_page = self.locate_callback(interaction.user)
        if found_page is not None:
            self.current_page = found_page
            # uses response.edit_message when possible; falls back to message.edit
            await self._safe_edit(interaction, self.pages[self.current_page])
        else:
            await interaction.response.send_message("🙅 You are not on the leaderboard.", ephemeral=True)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary, custom_id="next_page")
    async def next_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        self.current_page = (self.current_page + 1) % len(self.pages)
        await self.update_message(interaction)
