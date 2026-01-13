# cogs/misc/disboard/logic.py
from __future__ import annotations

import logging
import re
import discord

DISBOARD_ID = 302050872383242240

# Common phrases DISBOARD uses across locales/wordings
BUMP_DONE_PATTERNS = (
    "bump done",            # classic
    "bumped!",              # common variant
    "you can bump again",   # reset/cooldown phrasing
    "you can bump the server again",
)

USER_MENTION_RE = re.compile(r"<@!?(\d+)>")

def _lower(s: str | None) -> str:
    return (s or "").lower()

def _scan_embed_for_bump(embed: discord.Embed) -> tuple[bool, str | None, str | None]:
    """
    Return (is_bump, matched_phrase, location) where location is one of:
    'title', 'description', 'footer', 'field-name', 'field-value', or None.
    """
    checks: list[tuple[str | None, str]] = [
        (getattr(embed, "title", None), "title"),
        (embed.description, "description"),
        (getattr(getattr(embed, "footer", None), "text", None), "footer"),
    ]
    for f in getattr(embed, "fields", []) or []:
        checks.append((getattr(f, "name", None), "field-name"))
        checks.append((getattr(f, "value", None), "field-value"))

    for txt, loc in checks:
        hay = _lower(txt)
        if not hay:
            continue
        for p in BUMP_DONE_PATTERNS:
            if p in hay:
                return True, p, loc
    return False, None, None

def is_bump_confirmation_embed(embed: discord.Embed) -> bool:
    ok, _, _ = _scan_embed_for_bump(embed)
    return ok

async def find_latest_bump_message(
    channel: discord.TextChannel, *, limit: int = 200
) -> discord.Message | None:
    """Return the newest DISBOARD message containing a 'bump done' embed."""
    scanned = 0
    async for msg in channel.history(limit=limit):
        scanned += 1
        if msg.author.id != DISBOARD_ID or not msg.embeds:
            continue

        for e in msg.embeds:
            is_bump, matched, loc = _scan_embed_for_bump(e)
            if is_bump:
                logging.info(
                    "[Disboard] 🔎 Found bump confirmation: message_id=%s matched='%s' in=%s scanned=%d",
                    getattr(msg, "id", "unknown"),
                    matched,
                    loc,
                    scanned,
                )
                return msg

    logging.debug(
        "[Disboard] 🔎 No DISBOARD bump confirmation found after scanning %d messages (limit=%d)",
        scanned, limit
    )
    return None

def build_generic_reminder(guild_name: str) -> str:
    return (
        f"🔔 It's time to give **{guild_name}** a /bump! 🚀\n"
        f"✨ Who will be the next hero?"
    )

def _extract_user_from_embeds(bump_message: discord.Message) -> discord.abc.User | None:
    guild = getattr(bump_message, "guild", None)
    if not guild:
        return None

    for e in bump_message.embeds:
        text_blobs = [
            getattr(e, "title", "") or "",
            e.description or "",
            getattr(getattr(e, "footer", None), "text", "") or "",
        ]
        for f in getattr(e, "fields", []) or []:
            text_blobs.append((f.name or ""))
            text_blobs.append((f.value or ""))

        joined = "\n".join(text_blobs)
        m = USER_MENTION_RE.search(joined)
        if m:
            uid = int(m.group(1))
            member = guild.get_member(uid)
            if member:
                logging.info(
                    "[Disboard] 👤 Identified bumper via embed mention: user_id=%s display='%s'",
                    uid, getattr(member, "display_name", getattr(member, "name", str(uid)))
                )
                return member
            else:
                logging.info(
                    "[Disboard] 👤 Embed mention parsed but member not in cache: user_id=%s", uid
                )
    return None

def identify_bumper_user_with_source(
    bump_message: discord.Message,
) -> tuple[discord.abc.User | None, str]:
    """
    Returns (user, source) where source in:
    'interaction', 'message_mention', 'embed_mention', 'unknown'
    """
    try:
        interaction = getattr(bump_message, "interaction", None)
        if interaction and getattr(interaction, "user", None):
            user = interaction.user
            logging.info(
                "[Disboard] 👤 Bumper via interaction.user: user_id=%s display='%s'",
                getattr(user, "id", "unknown"),
                getattr(user, "display_name", getattr(user, "name", "unknown")),
            )
            return user, "interaction"
    except Exception as e:
        logging.warning("[Disboard] ⚠️ Error reading interaction.user: %r", e, exc_info=True)

    if bump_message.mentions:
        user = bump_message.mentions[0]
        logging.info(
            "[Disboard] 👤 Bumper via message mention: user_id=%s display='%s'",
            getattr(user, "id", "unknown"),
            getattr(user, "display_name", getattr(user, "name", "unknown")),
        )
        return user, "message_mention"

    user = _extract_user_from_embeds(bump_message)
    if user:
        return user, "embed_mention"

    return None, "unknown"

def identify_bumper_user(bump_message: discord.Message) -> discord.abc.User | None:
    user, _ = identify_bumper_user_with_source(bump_message)
    return user
