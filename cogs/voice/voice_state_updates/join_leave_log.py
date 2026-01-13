# cogs/voice_state_updates/join_leave_log.py
from __future__ import annotations

import discord
from configs.helper import send_as_webhook

async def log_join(member: discord.Member, channel: discord.VoiceChannel) -> None:
    await send_as_webhook(channel, "vc_join", content=f"🔊 **{member.display_name}** joined the voice channel.")

async def log_leave(member: discord.Member, channel: discord.VoiceChannel) -> None:
    await send_as_webhook(channel, "vc_leave", content=f"👋 **{member.display_name}** left the voice channel.")
