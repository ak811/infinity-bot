# cogs/economy/confirmation/cog.py
from __future__ import annotations

import discord
from discord.ext import commands
from cogs.economy._shared import set_confirmation
from configs.helper import send_as_webhook

class ConfirmationCog(commands.Cog):
    """!confirmation on/off — toggle receiver approval for incoming coin transfers."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="confirmation")
    async def confirmation_toggle(self, ctx: commands.Context, state: str | None = None):
        if state not in {"on", "off"}:
            embed = discord.Embed(
                title="❓ Confirmation — Help",
                description="Toggle whether you want to manually approve incoming coin transfers.",
                color=discord.Color.blurple(),
            )
            embed.add_field(name="Usage", value="`!confirmation on`\n`!confirmation off`", inline=False)
            embed.add_field(name="On",  value="You’ll be prompted to `!approve` or `!decline` when someone sends you coins.", inline=False)
            embed.add_field(name="Off", value="Coins sent to you will be accepted instantly without your approval.", inline=False)
            embed.set_footer(text="Tip: This only affects when you’re receiving coins.")
            await send_as_webhook(ctx, "confirmation", embed=embed)
            return

        set_confirmation(ctx.author.id, state == "on")

        if state == "on":
            embed = discord.Embed(
                title="✅ Confirmation Enabled",
                description="You will now be asked to `!approve` or `!decline` every time someone sends you coins.",
                color=discord.Color.green(),
            )
            await send_as_webhook(ctx, "confirmation_on", embed=embed)
        else:
            embed = discord.Embed(
                title="🙅 Confirmation Disabled",
                description="All incoming coins will now be accepted instantly without asking for your approval.",
                color=discord.Color.red(),
            )
            await send_as_webhook(ctx, "confirmation_off", embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ConfirmationCog(bot))
