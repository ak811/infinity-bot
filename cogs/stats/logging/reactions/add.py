# cogs/stats/logging/reactions/add.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable
import re
import discord
from configs.config_logging import logging
from configs.config_channels import LOGS_CHANNEL_ID
from configs.helper import send_as_webhook, edit_webhook_message

# Tweak as desired
MAX_PREVIEW_CHARS = 200

# Matches Markdown headings at the start of a line (or after a newline):
# "# Title", "## Title", ... up to "###### Title"
_HEADING_RE = re.compile(r'(^|\n)#{1,6}\s*', flags=re.MULTILINE)


def _strip_md_headings(text: str) -> str:
    """
    Remove Markdown heading markers (#, ##, ..., ######) at line starts.
    Does NOT touch inline # (e.g., #general) that aren't at line starts.
    """
    if not text:
        return ""
    return _HEADING_RE.sub(r"\1", text)


def _safe_preview(text: str, limit: int = MAX_PREVIEW_CHARS) -> str:
    """
    Make a short, single-line preview safe for logs:
      - strip Markdown heading markers at line starts
      - collapse whitespace/newlines
      - de-ping plain-text @ (e.g., @alex), but DO NOT touch real mention tokens like <@123>, <@!123>, <@&123>
      - truncate and add ellipsis
    """
    if not text:
        return ""

    # 1) Strip leading Markdown heading hashes
    text = _strip_md_headings(text)

    # 2) Collapse whitespace/newlines
    s = " ".join(text.strip().split())

    # 3) De-ping only non-mention @
    #    - keep <@123>, <@!123>, <@&123> intact (so they resolve)
    #    - neutralize other @ to avoid accidental pings (e.g., @alex.k)
    #    Regex: an '@' that is NOT preceded by '<' and NOT followed by (! or &) and digits ending with '>'
    import re
    s = re.sub(r'(?<!<)@(?!(?:!|&)?\d+>)', '@\u200b', s)

    # 4) Truncate
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "…"

    return s


def _extract_message_preview(message: discord.Message) -> str:
    """
    Combine author message content + a bit from the first embed (title/description),
    then sanitize and truncate.
    """
    parts: list[str] = []
    if message.content:
        parts.append(message.content)

    if message.embeds:
        e = message.embeds[0]
        # Pull the most useful short bits from the first embed
        e_bits: Iterable[str] = filter(None, [e.title, e.description])
        e_text = " — ".join(e_bits)
        if e_text:
            parts.append(e_text)

    raw = " | ".join(parts).strip()
    return _safe_preview(raw)


def build_reaction_embed(
    *,
    donor_id: int,
    recipient_id: int,
    jump_url: str,
    channel_id: int,
    emoji_items: list[tuple[str, str]],  # [(icon, name)]
    title: str = "🧩 Reactions Added",
    message_preview: str | None = None,  # stays inside description
) -> discord.Embed:
    icons = ", ".join(icon for icon, _ in emoji_items)
    names = ", ".join((nm or "emoji") for _, nm in emoji_items)

    description = (
        f"{icons} <@{donor_id}> **reacted with {names}** to "
        f"<@{recipient_id}>'s [message]({jump_url}) in <#{channel_id}>"
    )

    # Keep everything in the embed description, include a quoted, sanitized preview
    if message_preview:
        description += f"\n\n> {message_preview}"

    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blurple(),
        timestamp=datetime.now(timezone.utc),
    )


async def upsert_reaction_log(
    bot: discord.Client,
    *,
    donor: discord.User | discord.Member,
    recipient_id: int,
    jump_url: str,
    channel_id: int,
    emoji_items: list[tuple[str, str]],  # [(icon, name)]
    existing_token: tuple[int, int | None, int] | None,  # (log_channel_id, webhook_id_or_none, message_id)
    message_preview: str | None = None,  # embed-only
) -> tuple[int, int | None, int] | None:
    """
    Create or edit the single log message for (guild, channel, message, donor).
    Returns (channel_id, webhook_id_or_none, message_id).
    """
    try:
        target = bot.get_channel(LOGS_CHANNEL_ID) or await bot.fetch_channel(LOGS_CHANNEL_ID)
        if not isinstance(target, (discord.TextChannel, discord.Thread)):
            logging.warning("[ReactionLog] LOGS_CHANNEL_ID is not a text channel/thread.")
            return None

        embed = build_reaction_embed(
            donor_id=donor.id,
            recipient_id=recipient_id,
            jump_url=jump_url,
            channel_id=channel_id,
            emoji_items=emoji_items,
            message_preview=message_preview,  # stays inside embed description
        )

        if existing_token is None:
            # CREATE (embed-only)
            m = await send_as_webhook(target, "reactions", embed=embed)  # type: ignore
            if m is None:
                logging.warning("[ReactionLog] send_as_webhook returned None.")
                return None
            token = (target.id, getattr(m, "webhook_id", None), m.id)
            return token

        # EDIT (embed-only)
        ch_id, wh_id, msg_id = existing_token
        ok = await edit_webhook_message(
            bot, ch_id, wh_id, msg_id, embed=embed
        )
        if not ok:
            # Re-create only if edit truly failed
            m = await send_as_webhook(target, "reactions", embed=embed)  # type: ignore
            if m is None:
                logging.warning("[ReactionLog] re-create after edit failure returned None.")
                return existing_token
            return (target.id, getattr(m, "webhook_id", None), m.id)

        return existing_token

    except Exception as e:
        logging.warning(f"[ReactionLog] Failed to upsert reaction log: {e}")
        return None
