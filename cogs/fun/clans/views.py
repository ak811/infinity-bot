# cogs/clans/views.py
import discord
from typing import List

class PagedView(discord.ui.View):
    def __init__(self, pages: List[discord.Embed], timeout: float = 120):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.index = 0

    def current(self) -> discord.Embed:
        e = self.pages[self.index]
        e.set_footer(text=f"Page {self.index+1}/{len(self.pages)} • Use ◀️ ▶️")
        return e

    async def send(self, ctx):
        await ctx.send(embed=self.current(), view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.current(), view=self)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.pages)
        await interaction.response.edit_message(embed=self.current(), view=self)
