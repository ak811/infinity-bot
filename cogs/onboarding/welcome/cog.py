# cogs/welcome/cog.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands
from dateutil.relativedelta import relativedelta

from configs.config_channels import WELCOME_CHANNEL_ID
from configs.config_roles import MEMBER_ROLE_ID

from .helpers import member_has_loot_legends_role


class WelcomeCog(commands.Cog):
    """Assign newcomer role and post a rich welcome embed in the welcome channel."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)

    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        # Only the configured channel
        if not isinstance(message.channel, discord.TextChannel) or message.channel.id != WELCOME_CHANNEL_ID:
            return

        # Must be in a guild and not from a bot
        if not message.guild or message.author.bot:
            return

        member = message.author
        assert isinstance(member, discord.Member)

        # Skip if already has a Loot & Legends role
        if member_has_loot_legends_role(member):
            return

        # Assign newcomer/member role if missing
        newcomer_role = message.guild.get_role(MEMBER_ROLE_ID)
        if newcomer_role is None or newcomer_role in member.roles:
            # Either no such role, or member already has it — still try to post embed below
            pass
        else:
            try:
                await member.add_roles(newcomer_role, reason="Welcome processing")
            except Exception as e:
                self.log.warning(f"[Welcome] Failed to add newcomer role to {member}: {e}")

        # Fetch full user for banner if needed
        try:
            full_user = await self.bot.fetch_user(member.id)
        except Exception:
            full_user = member  # graceful fallback; banner may be missing

        # Account age
        try:
            account_age = relativedelta(datetime.now(timezone.utc), member.created_at)
            age_parts = []
            if account_age.years:
                age_parts.append(f"{account_age.years} year{'s' if account_age.years > 1 else ''}")
            if account_age.months:
                age_parts.append(f"{account_age.months} month{'s' if account_age.months > 1 else ''}")
            if account_age.days:
                age_parts.append(f"{account_age.days} day{'s' if account_age.days > 1 else ''}")
            age_display = ", ".join(age_parts) if age_parts else "0 days"
        except Exception:
            age_display = "unknown"

        username = str(member)
        display_name = member.display_name
        # Exclude @everyone at index 0; show other roles newest→oldest
        roles = [role.mention for role in reversed(member.roles[1:])] if len(member.roles) > 1 else []
        roles_display = ", ".join(roles) if roles else "None"
        banner_url = getattr(getattr(full_user, "banner", None), "url", None)

        embed = discord.Embed(
            title="🎉 Welcome to the Server!",
            description=(
                f"Hey {member.mention}, we're so glad you joined us! 😊\n\n"
                f"__**About You**__\n"
                f"**Name:** {display_name}\n"
                f"**Username:** {username}\n"
                f"**Account Age:** {age_display}\n"
                f"**Roles:** {roles_display}\n\n"
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.utcnow(),
        )

        try:
            thumb_url = member.avatar.url if member.avatar else (message.guild.icon.url if message.guild.icon else None)
            if thumb_url:
                embed.set_thumbnail(url=thumb_url)
        except Exception:
            pass

        if banner_url:
            try:
                embed.set_image(url=banner_url)
            except Exception:
                pass

        try:
            if message.guild and message.guild.icon:
                embed.set_footer(text="Enjoy your time here!", icon_url=message.guild.icon.url)
            else:
                embed.set_footer(text="Enjoy your time here!")
        except Exception:
            embed.set_footer(text="Enjoy your time here!")

        try:
            content = f"💫 Everyone welcome {member.mention}!"
            await message.channel.send(content=content, embed=embed)
        except Exception as e:
            self.log.error(f"[Welcome] Failed to send welcome embed for {member}: {e}", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
