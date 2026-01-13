# cogs/server/avatar/cog.py
from __future__ import annotations

import discord
from discord.ext import commands

from configs.helper import send_as_webhook, PERSONAS

FALLBACK_IMAGE_PATH = "database/images/server_profile.png"
FALLBACK_IMAGE_NAME = "server_profile.png"

class AvatarCog(commands.Cog):
    """
    !avatar — show a member's avatar with your custom webhook persona.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="avatar")
    async def avatar(self, ctx: commands.Context, member: discord.Member | None = None):
        """
        Shows the avatar of the given user, or the command author if no user is mentioned,
        using the custom persona display.
        """
        target = member or ctx.author

        async with ctx.typing():
            avatar_url = target.display_avatar.url

            embed = discord.Embed(
                title=f"{target.display_name}'s Avatar",
                color=discord.Color.blue(),
            )
            embed.set_image(url=avatar_url)

            # If the user has no custom avatar, attach a local fallback image so Discord shows a preview nicely
            file = None
            if not target.avatar:
                file = discord.File(FALLBACK_IMAGE_PATH, filename=FALLBACK_IMAGE_NAME)

            # Register / update the "custom" persona for this message
            PERSONAS["custom"] = {
                "name": target.display_name,
                "avatar": avatar_url,
            }

            await send_as_webhook(
                ctx,
                pet_type="custom",
                embed=embed,
                file=file
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(AvatarCog(bot))
