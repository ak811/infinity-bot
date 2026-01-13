# cogs/embeds/cog.py
from __future__ import annotations

import discord
from discord.ext import commands

from .quick_guide import build_quick_guide_embeds, QUICK_GUIDE_CHANNEL_ID, QUICK_GUIDE_MESSAGE_ID
from .roles_and_channels import (
    update_roles_and_commands_embeds as _update_roles_and_commands_embeds,
    update_channels_embed_only as _update_channels_embed_only,
)

class EmbedsCog(commands.Cog):
    """Builds and updates server embeds: Quick Guide, Commands, Roles/Perks, Channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Public methods you can call elsewhere ─────────────────────────────────
    async def update_quick_guide_message(self) -> None:
        channel = self.bot.get_channel(QUICK_GUIDE_CHANNEL_ID)
        if not isinstance(channel, (discord.TextChannel, discord.Thread, discord.ForumChannel)):
            print("🙅 QUICK_GUIDE_CHANNEL_ID not found or not a text-capable channel.")
            return

        try:
            msg = await channel.fetch_message(QUICK_GUIDE_MESSAGE_ID)
        except discord.Forbidden:
            print("🙅 Permission error: cannot fetch the Quick Guide message.")
            return
        except discord.NotFound:
            print("🙅 Not found: Quick Guide message ID is wrong or message deleted.")
            return

        embeds = build_quick_guide_embeds()
        try:
            await msg.edit(content=None, embeds=embeds)
            print("✅ Updated Quick Guide message.")
        except discord.Forbidden:
            print("🙅 Permission error: cannot edit the Quick Guide message.")
        except discord.HTTPException as e:
            print(f"🙅 Discord HTTP error while editing message: {e}")
        except Exception as e:
            print(f"🙅 Failed to update Quick Guide message: {e}")

    async def update_roles_and_commands_embeds(self) -> None:
        try:
            await _update_roles_and_commands_embeds(self.bot)
            print("✅ Updated commands / perks / channels messages.")
        except discord.Forbidden:
            print("🙅 Permission error: fetch/edit failed for one of the messages.")
        except discord.NotFound:
            print("🙅 Not found: a target message ID is wrong or was deleted.")
        except Exception as e:
            print(f"🙅 Failed to update messages: {e}")

    async def update_channels_embed_only(self) -> None:
        try:
            await _update_channels_embed_only(self.bot)
            print("✅ Updated channels message.")
        except discord.Forbidden:
            print("🙅 Permission error: cannot fetch/edit channels message.")
        except discord.NotFound:
            print("🙅 Not found: channels message not found with the given ID.")
        except Exception as e:
            print(f"🙅 Failed to update channels message: {e}")

    # ── Optional convenience commands (restrict appropriately) ────────────────
    @commands.command(name="sudo_refresh_quick_guide")
    @commands.has_permissions(manage_guild=True)
    async def cmd_refresh_quick_guide(self, ctx: commands.Context):
        await self.update_quick_guide_message()
        await ctx.reply("🧼 Quick Guide refreshed.", mention_author=False)

    @commands.command(name="sudo_refresh_embeds")
    @commands.has_permissions(manage_guild=True)
    async def cmd_refresh_embeds(self, ctx: commands.Context):
        await self.update_roles_and_commands_embeds()
        await ctx.reply("🧼 Commands/Perks/Channels refreshed.", mention_author=False)

    @commands.command(name="sudo_refresh_channels")
    @commands.has_permissions(manage_guild=True)
    async def cmd_refresh_channels(self, ctx: commands.Context):
        await self.update_channels_embed_only()
        await ctx.reply("🧼 Channels embed refreshed.", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(EmbedsCog(bot))
