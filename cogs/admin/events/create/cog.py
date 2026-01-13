from __future__ import annotations
import discord
from discord.ext import commands
import pytz
from datetime import datetime, timedelta
from configs.config_channels import BOOK_CLUB_CHANNEL_ID

DEFAULT_TIMEZONE = "America/New_York"
DEFAULT_HOURS_AHEAD = 2
DEFAULT_DESCRIPTION = "Join us for an exciting event!"

class CreateEventCog(commands.Cog):
    """sudo_create_event "Name" [YYYY-MM-DD] [HH:MM] [channel_id] ["Description"]"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sudo_create_event")
    @commands.has_permissions(administrator=True)
    async def sudo_create_event(self, ctx, name: str, date: str = None, time: str = None, channel_id: int | None = None, description: str | None = None):
        try:
            tz = pytz.timezone(DEFAULT_TIMEZONE)
            if date and time:
                naive = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                local_dt = tz.localize(naive)
            else:
                local_dt = datetime.now(tz) + timedelta(hours=DEFAULT_HOURS_AHEAD)

            utc_time = local_dt.astimezone(pytz.utc)
            channel = ctx.guild.get_channel(channel_id) if channel_id else ctx.guild.get_channel(BOOK_CLUB_CHANNEL_ID)
            if not channel:
                await ctx.send("🙅 Could not find the specified voice channel.")
                return

            desc = description or DEFAULT_DESCRIPTION
            event = await ctx.guild.create_scheduled_event(
                name=name,
                start_time=utc_time,
                description=desc,
                channel=channel,
                entity_type=discord.EntityType.voice,
                privacy_level=discord.PrivacyLevel.guild_only
            )
            await ctx.send(f"✅ Event **{event.name}** scheduled for {local_dt.strftime('%Y-%m-%d %H:%M %Z')} in {channel.mention}!")
        except Exception as e:
            await ctx.send(f"🙅 Failed to create event: {str(e)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(CreateEventCog(bot))
