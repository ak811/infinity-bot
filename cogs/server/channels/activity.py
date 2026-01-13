# cogs/server/channels/activity.py
from __future__ import annotations
import discord, asyncio
from datetime import datetime, timedelta, timezone
from ._storage import load_activity, save_activity
from .archive_config import (
    INACTIVITY_DAYS, ARCHIVE_TEXT, ARCHIVE_VOICE, REQUIRE_PUBLIC,
    VC_REQUIRE_RECENT_MESSAGE
)

# Use STRING KEYS for channel IDs to avoid duplicate JSON keys
_last_text_ts: dict[str, str] = {}
_last_voice_ts: dict[str, str] = {}
_bootstrapped = False
_save_lock = asyncio.Lock()

def _now() -> datetime: return datetime.now(timezone.utc)
def _iso(dt: datetime) -> str: return dt.astimezone(timezone.utc).isoformat()
def _parse(s: str) -> datetime: return datetime.fromisoformat(s)
def _key_id(cid: int | str) -> str: return str(cid)

def _is_public(ch: discord.abc.GuildChannel) -> bool:
    try: return ch.permissions_for(ch.guild.default_role).view_channel
    except Exception: return False

async def _persist():
    async with _save_lock:
        await save_activity({"text": _last_text_ts, "voice": _last_voice_ts})

async def bootstrap(bot: discord.Client) -> None:
    global _bootstrapped, _last_text_ts, _last_voice_ts
    if _bootstrapped: return

    data = await load_activity()
    _last_text_ts  = { _key_id(k): v for k, v in (data.get("text")  or {}).items() }
    _last_voice_ts = { _key_id(k): v for k, v in (data.get("voice") or {}).items() }

    async def seed_textlike(ch: discord.abc.GuildChannel):
        # Seed last message timestamp for both TextChannels and VoiceChannels (voice chat)
        kid = _key_id(ch.id)
        if kid in _last_text_ts: return
        if REQUIRE_PUBLIC and not _is_public(ch): return
        # Only attempt history on channels that are messageable
        if not hasattr(ch, "history"): return
        try:
            async for m in ch.history(limit=1, oldest_first=False):
                ts = m.created_at if m.created_at.tzinfo else m.created_at.replace(tzinfo=timezone.utc)
                _last_text_ts[kid] = _iso(ts)
                break
        except Exception:
            pass

    for g in bot.guilds:
        if ARCHIVE_TEXT:
            for ch in g.text_channels:
                await seed_textlike(ch)
        if ARCHIVE_VOICE:
            # seed VC message timestamps too (if any)
            for v in g.voice_channels:
                await seed_textlike(v)
                if REQUIRE_PUBLIC and not _is_public(v): continue
                if v.members:
                    _last_voice_ts[_key_id(v.id)] = _iso(_now())

    await _persist()
    _bootstrapped = True

async def update_from_message(message: discord.Message) -> None:
    # Count messages in TextChannels and VoiceChannels
    ch = message.channel
    if not isinstance(ch, (discord.TextChannel, discord.VoiceChannel)):
        return
    if REQUIRE_PUBLIC and not _is_public(ch):
        return
    _last_text_ts[_key_id(ch.id)] = _iso(_now())
    await _persist()

async def update_from_voice_state(member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    if not ARCHIVE_VOICE: return
    now = _iso(_now())
    for vc in (before.channel, after.channel):
        if not vc: continue
        if REQUIRE_PUBLIC and not _is_public(vc): continue
        _last_voice_ts[_key_id(vc.id)] = now
    await _persist()

async def _last_message_recent(channel: discord.abc.GuildChannel, cutoff: datetime) -> bool:
    kid = _key_id(channel.id)
    ts = _last_text_ts.get(kid)
    if not ts and hasattr(channel, "history"):
        # lazy fetch if unseen
        try:
            async for m in channel.history(limit=1, oldest_first=False):
                ts_iso = _iso(m.created_at if m.created_at.tzinfo else m.created_at.replace(tzinfo=timezone.utc))
                _last_text_ts[kid] = ts_iso
                await _persist()
                ts = ts_iso
                break
        except Exception:
            pass
    return bool(ts) and _parse(ts) >= cutoff

async def is_channel_active(channel: discord.abc.GuildChannel) -> bool:
    if REQUIRE_PUBLIC and not _is_public(channel):
        return True
    cutoff = _now() - timedelta(days=INACTIVITY_DAYS)

    if isinstance(channel, discord.TextChannel):
        return await _last_message_recent(channel, cutoff)

    if isinstance(channel, discord.VoiceChannel):
        # 1) live occupancy is always active
        if getattr(channel, "members", None) and len(channel.members) > 0:
            # Refresh voice ts for consistency
            _last_voice_ts[_key_id(channel.id)] = _iso(_now())
            await _persist()
            return True

        # 2) If configured, *require* recent message in the VC's chat
        if VC_REQUIRE_RECENT_MESSAGE:
            return await _last_message_recent(channel, cutoff)

        # 3) Otherwise, accept either recent message OR recent voice activity
        if await _last_message_recent(channel, cutoff):
            return True
        ts = _last_voice_ts.get(_key_id(channel.id))
        return bool(ts) and _parse(ts) >= cutoff

    return True
