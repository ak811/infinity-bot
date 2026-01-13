from __future__ import annotations

import random, asyncio
import discord
from discord.ext import commands
from configs.config_logging import logging
from configs.helper import send_as_webhook

class DiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="dice")
    async def dice(self, ctx: commands.Context):
        """Roll a dice with a short animation; edits a single message."""
        embed = discord.Embed(title="🎲 Dice", description="Rolling the dice...", color=discord.Color.orange())
        message = await send_as_webhook(ctx, "dice", embed=embed)

        for _ in range(5):
            roll = random.randint(1, 6)
            await asyncio.sleep(0.5)
            anim = discord.Embed(title="🎲 Dice", description=f"Rolling... **{roll}**", color=discord.Color.orange())
            await message.edit(embed=anim)
            logging.info(f"[Dice] Edited message {message.id} to {roll}")

        final_roll = random.randint(1, 6)
        result = discord.Embed(title="🎲 Dice Result", description=f"The dice landed on **{final_roll}**!", color=discord.Color.green())
        await message.edit(embed=result)
        logging.info(f"[Dice] Final roll (edited): {final_roll}")

async def setup(bot: commands.Bot):
    await bot.add_cog(DiceCog(bot))
