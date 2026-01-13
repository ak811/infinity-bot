# cogs/server/emojis/pagination.py
from __future__ import annotations
import discord
from typing import List, Optional, Union

# A page can be: a single embed, a list of embeds (grid), or plain text
Page = Union[discord.Embed, List[discord.Embed], str]


def message_kwargs_for_page(page: Page) -> dict:
    """Return kwargs suitable for ctx.send(...) or interaction.response.edit_message(...)."""
    if isinstance(page, list):
        # A "grid" page composed of multiple embeds
        return {"embeds": page}
    if isinstance(page, discord.Embed):
        return {"embed": page}
    # Fallback to content-only (useful to trigger jumbo emoji rendering elsewhere)
    return {"content": str(page), "attachments": [], "embed": None}


class PaginatorView(discord.ui.View):
    def __init__(self, pages: List[Page], *, start: int = 0, author_id: Optional[int] = None, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = max(0, min(start, len(pages) - 1))
        self.author_id = author_id
        self._sync_button_states()

    def _sync_button_states(self):
        # disable/enable buttons depending on position
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "p.left":
                    child.disabled = (self.index <= 0)
                elif child.custom_id == "p.right":
                    child.disabled = (self.index >= len(self.pages) - 1)

    async def _update(self, interaction: discord.Interaction):
        self._sync_button_states()
        await interaction.response.edit_message(view=self, **message_kwargs_for_page(self.pages[self.index]))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # If author_id provided, only they can page.
        return (self.author_id is None) or (interaction.user and interaction.user.id == self.author_id)

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary, custom_id="p.left")
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await self._update(interaction)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary, custom_id="p.right")
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
            await self._update(interaction)


class PaginatorTextView(discord.ui.View):
    """Paginator for plain-text pages (no embeds). Keeps content emoji-only to trigger jumbo size."""
    def __init__(self, pages: List[str], *, start: int = 0, author_id: Optional[int] = None, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = max(0, min(start, len(pages) - 1))
        self.author_id = author_id
        self._sync_button_states()

    def _sync_button_states(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "pt.left":
                    child.disabled = (self.index <= 0)
                elif child.custom_id == "pt.right":
                    child.disabled = (self.index >= len(self.pages) - 1)

    async def _update(self, interaction: discord.Interaction):
        self._sync_button_states()
        # Content-only (no embeds/attachments) ensures "jumbo emoji" rendering when content is only emojis/spaces.
        await interaction.response.edit_message(content=self.pages[self.index], attachments=[], embed=None, view=self)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return (self.author_id is None) or (interaction.user and interaction.user.id == self.author_id)

    @discord.ui.button(emoji="⬅️", style=discord.ButtonStyle.secondary, custom_id="pt.left")
    async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index > 0:
            self.index -= 1
            await self._update(interaction)

    @discord.ui.button(emoji="➡️", style=discord.ButtonStyle.secondary, custom_id="pt.right")
    async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.index < len(self.pages) - 1:
            self.index += 1
            await self._update(interaction)
