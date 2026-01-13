# cogs/voice_state_updates/cog.py
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from configs.config_general import BOT_GUILD_ID
from cogs.economy.xp.service import update_xp  # thin wrapper → xp.service.update_xp
from .move_active_vc import move_active_vc
from .join_leave_log import log_join, log_leave

log = logging.getLogger(__name__)


class VoiceStateUpdatesCog(commands.Cog):
    """
    Handles:
      - VC join/leave/switch events
      - Per-user debounced 'post-join' tasks
      - VC time → XP (vc_seconds via update_xp)
      - Auto-floating active VC under Join-to-Create (exclusions respected)
      - (Optional) initialize currently active VC users at startup
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Track active VC session start times per user
        self.join_times: dict[str, datetime] = {}
        # Debounce tasks per-user to coalesce multiple voice events
        self.voice_join_tasks: dict[int, asyncio.Task] = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    async def _wait_until_joined(
        self,
        member: discord.Member,
        channel: discord.VoiceChannel,
        timeout: float = 5.0,
        tick: float = 0.15,
    ) -> bool:
        """Poll until the member is confirmed inside the channel."""
        loop = asyncio.get_event_loop()
        start = loop.time()
        while (loop.time() - start) < timeout:
            fresh = member.guild.get_channel(channel.id)
            if isinstance(fresh, discord.VoiceChannel):
                if member.voice and member.voice.channel and member.voice.channel.id == channel.id:
                    if any(m.id == member.id for m in fresh.members):
                        return True
            await asyncio.sleep(tick)
        return False

    async def _schedule_post_join(self, member: discord.Member, channel: discord.VoiceChannel) -> None:
        """Delayed tasks after a join event — send join log, keep room for more hooks."""
        # cancel previous pending task for this user
        t = self.voice_join_tasks.pop(member.id, None)
        if t and not t.done():
            t.cancel()

        async def _run():
            try:
                await asyncio.sleep(0.75)
                ok = await self._wait_until_joined(member, channel, timeout=4.0)
                if not ok:
                    log.warning(f"[voice] join not settled for {member.display_name} in {channel.name}")
                    return
                try:
                    await log_join(member, channel)
                except Exception as e:
                    log.warning(f"[VC] join log failed for {channel.name}: {e}")
            except asyncio.CancelledError:
                pass

        self.voice_join_tasks[member.id] = asyncio.create_task(_run())

    async def _log_active_vc_users(self, guild: discord.Guild) -> None:
        """Initializes join times for all currently active VC users."""
        for vc in guild.voice_channels:
            if vc == guild.afk_channel:
                continue
            for member in vc.members:
                if not member.bot and str(member.id) not in self.join_times:
                    self.join_times[str(member.id)] = datetime.utcnow()
                    log.info(f"[VC] Logged existing join for {member} in {vc.name}")

    # ──────────────────────────────────────────────────────────────────────────
    # Listeners
    # ──────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_ready")
    async def _init_active_sessions(self):
        # Optional best-effort init (guild cache available after ready)
        try:
            guild = self.bot.get_guild(int(BOT_GUILD_ID))
            if guild:
                await self._log_active_vc_users(guild)
        except Exception as e:
            log.warning(f"[voice] init active sessions failed: {e}")

    @commands.Cog.listener("on_voice_state_update")
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Main entry point for voice state events."""
        try:
            # Ignore bots and other guilds
            if not member.guild or int(member.guild.id) != int(BOT_GUILD_ID) or member.bot:
                return
            await self._handle_voice_channel_events(member, before, after)
        except Exception as e:
            log.error(f"[voice] Unexpected error in on_voice_state_update: {e}", exc_info=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Core handler
    # ──────────────────────────────────────────────────────────────────────────

    async def _handle_voice_channel_events(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        user_id = str(member.id)
        guild = member.guild
        afk_channel = guild.afk_channel  # dynamically get AFK channel

        # User JOINS a VC (none -> some)
        if before.channel is None and after.channel is not None:
            self.join_times[user_id] = datetime.utcnow()
            log.info(f"[voice] {member.display_name} joined VC {after.channel.name}")

            # Move VC below JTC unless it's AFK
            if not afk_channel or after.channel.id != afk_channel.id:
                await move_active_vc(after.channel)

            await self._schedule_post_join(member, after.channel)

        # User LEAVES a VC (some -> none)
        elif before.channel is not None and after.channel is None:
            # Skip XP updates if leaving AFK
            if afk_channel and before.channel.id == afk_channel.id:
                self.join_times.pop(user_id, None)
                return

            # Grant XP for time spent
            if user_id in self.join_times:
                join_time = self.join_times.pop(user_id)
                duration = int((datetime.utcnow() - join_time).total_seconds())
                if duration > 0:
                    update_xp(user_id, duration, "vc")

            # Log leave
            try:
                await log_leave(member, before.channel)
            except Exception as e:
                log.warning(f"[VC] leave log failed for {before.channel.name}: {e}")

            # Cancel any pending post-join tasks
            t = self.voice_join_tasks.pop(member.id, None)
            if t and not t.done():
                t.cancel()

        # User SWITCHES between VCs (some -> different some)
        elif before.channel and after.channel and before.channel.id != after.channel.id:
            # Ignore AFK transitions entirely
            if afk_channel and (before.channel.id == afk_channel.id or after.channel.id == afk_channel.id):
                return

            # Log leave in the old VC
            try:
                await log_leave(member, before.channel)
            except Exception as e:
                log.warning(f"[voice] leave log failed for {before.channel.name}: {e}")

            # Grant XP for old VC
            if user_id in self.join_times:
                join_time = self.join_times[user_id]
                duration = int((datetime.utcnow() - join_time).total_seconds())
                if duration > 0:
                    update_xp(user_id, duration, "vc")

            # Treat as new join in the destination VC
            self.join_times[user_id] = datetime.utcnow()

            # Move VC below JTC unless it's AFK
            if not afk_channel or after.channel.id != afk_channel.id:
                await move_active_vc(after.channel)

            await self._schedule_post_join(member, after.channel)


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceStateUpdatesCog(bot))
