# cogs/vc_name_update/cog.py
from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

# CHANGED: import the new formatter
from .end_of_month import format_reset_label
from .member_count import build_member_count_name

log = logging.getLogger(__name__)

# ── Configure your channel IDs here ────────────────────────────────────────────
# Voice/Stage channel that shows the time remaining until next reset Saturday.
COUNTDOWN_CHANNEL_ID = 1415896576534122557

# Voice/Stage channel that shows the current member count.
MEMBER_COUNT_CHANNEL_ID = 1431397590343352350

# If you prefer "humans only" count, set to False.
INCLUDE_BOTS_IN_COUNT = True
# ───────────────────────────────────────────────────────────────────────────────


class VCNameUpdate(commands.Cog):
    """Renames specific VC channels for Reset-of-Month countdown and Member Count."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._started = False

        # Loop intervals
        self.update_month_end_countdown_loop.change_interval(minutes=6)
        self.refresh_member_count_loop.change_interval(minutes=10)

    # ── helpers ────────────────────────────────────────────────────────────────
    async def _resolve_channel(self, channel_id: int) -> discord.abc.GuildChannel | None:
        ch = self.bot.get_channel(channel_id)
        if ch:
            return ch
        try:
            return await self.bot.fetch_channel(channel_id)
        except Exception as e:
            log.error(f"[vc_name_update] fetch_channel({channel_id}) failed: {e}")
            return None

    async def _safe_rename(self, channel: discord.abc.GuildChannel, new_name: str) -> None:
        if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
            log.warning(f"[vc_name_update] Target {channel.id} is not a voice/stage channel.")
            return

        me = channel.guild.me
        if me is None:
            log.warning("[vc_name_update] guild.me is None; check intents (guilds).")
            return

        if not channel.permissions_for(me).manage_channels:
            log.error(f"[vc_name_update] Missing 'Manage Channels' permission on {channel.name} ({channel.id}).")
            return

        if channel.name != new_name:
            try:
                await channel.edit(name=new_name)
                log.info(f"[vc_name_update] Renamed '{channel.name}' -> '{new_name}'")
            except discord.HTTPException as e:
                log.error(f"[vc_name_update] HTTPException while renaming {channel.id}: {e}")
            except Exception as e:
                log.error(f"[vc_name_update] Unexpected error renaming {channel.id}: {e}")

    # ── loops ──────────────────────────────────────────────────────────────────
    @tasks.loop(minutes=6, reconnect=True)
    async def update_month_end_countdown_loop(self):
        try:
            now_utc = datetime.now(timezone.utc)
            # CHANGED: use the new label
            new_name = format_reset_label(now_utc)
            ch = await self._resolve_channel(COUNTDOWN_CHANNEL_ID)
            if ch:
                await self._safe_rename(ch, new_name)
            else:
                log.warning("[vc_name_update] Countdown channel not found.")
        except Exception as e:
            log.error(f"[vc_name_update] Reset-of-month loop error: {e}", exc_info=True)

    @tasks.loop(minutes=10, reconnect=True)
    async def refresh_member_count_loop(self):
        try:
            ch = await self._resolve_channel(MEMBER_COUNT_CHANNEL_ID)
            if not ch or not isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                log.warning("[vc_name_update] Member-count channel not found or wrong type.")
                return
            new_name = build_member_count_name(ch.guild, include_bots=INCLUDE_BOTS_IN_COUNT)
            await self._safe_rename(ch, new_name)
        except Exception as e:
            log.error(f"[vc_name_update] Member-count loop error: {e}", exc_info=True)

    @update_month_end_countdown_loop.before_loop
    async def _before_eom(self):
        await self.bot.wait_until_ready()
        # Kick an initial rename
        try:
            ch = await self._resolve_channel(COUNTDOWN_CHANNEL_ID)
            if ch:
                name = format_reset_label(datetime.now(timezone.utc))
                await self._safe_rename(ch, name)
            log.info("[vc_name_update] Reset-of-month countdown loop starting.")
        except Exception as e:
            log.error(f"[vc_name_update] Initial reset-of-month rename failed: {e}")

    @refresh_member_count_loop.before_loop
    async def _before_member_count(self):
        await self.bot.wait_until_ready()
        # Kick an initial rename
        try:
            ch = await self._resolve_channel(MEMBER_COUNT_CHANNEL_ID)
            if ch and isinstance(ch, (discord.VoiceChannel, discord.StageChannel)):
                name = build_member_count_name(ch.guild, include_bots=INCLUDE_BOTS_IN_COUNT)
                await self._safe_rename(ch, name)
            log.info("[vc_name_update] Member-count loop starting.")
        except Exception as e:
            log.error(f"[vc_name_update] Initial member-count rename failed: {e}")

    # ── listeners: react instantly on join/leave ───────────────────────────────
    @commands.Cog.listener("on_ready")
    async def _start_loops_once(self):
        if self._started:
            return
        self._started = True
        self.update_month_end_countdown_loop.start()
        self.refresh_member_count_loop.start()

    @commands.Cog.listener("on_member_join")
    async def _on_join(self, member: discord.Member):
        # Only refresh for the guild that has the target channel
        ch = self.bot.get_channel(MEMBER_COUNT_CHANNEL_ID) or await self._resolve_channel(MEMBER_COUNT_CHANNEL_ID)
        if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)) and ch.guild.id == member.guild.id:
            name = build_member_count_name(ch.guild, include_bots=INCLUDE_BOTS_IN_COUNT)
            await self._safe_rename(ch, name)

    @commands.Cog.listener("on_member_remove")
    async def _on_leave(self, member: discord.Member):
        ch = self.bot.get_channel(MEMBER_COUNT_CHANNEL_ID) or await self._resolve_channel(MEMBER_COUNT_CHANNEL_ID)
        if isinstance(ch, (discord.VoiceChannel, discord.StageChannel)) and ch.guild.id == member.guild.id:
            name = build_member_count_name(ch.guild, include_bots=INCLUDE_BOTS_IN_COUNT)
            await self._safe_rename(ch, name)


async def setup(bot: commands.Bot):
    await bot.add_cog(VCNameUpdate(bot))