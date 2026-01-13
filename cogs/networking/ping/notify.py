# cogs/ping/notify.py
from __future__ import annotations
import discord

from .config import MAX_PING_SIZE, ALLOW_OPTIONAL_MESSAGE
from configs.helper import send_as_webhook

def _sanitize_message(msg: str) -> str:
    if not msg:
        return ""
    # basic defense-in-depth: avoid literal @everyone/@here text
    msg = msg.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
    if len(msg) > MAX_PING_SIZE:
        msg = msg[:MAX_PING_SIZE - 1] + "…"
    return msg

async def send_ping(ctx, role: discord.Role, message: str | None) -> None:
    content_parts = [role.mention]
    if ALLOW_OPTIONAL_MESSAGE and message:
        content_parts.append(_sanitize_message(message))
    content = " ".join(content_parts).strip()

    allowed = discord.AllowedMentions(roles=True, users=False, everyone=False)

    try:
        # await ctx.send(content, allowed_mentions=allowed)
        await send_as_webhook(ctx, "ping", content=content)
    except discord.Forbidden:
        # If pings are blocked, at least show an info embed
        embed = discord.Embed(
            title="ℹ️ Mention blocked",
            description=f"I couldn't mention {role.mention} in this channel.",
            color=discord.Color.orange()
        )
        await send_as_webhook(ctx, "ping", embed=embed)
