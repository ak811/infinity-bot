# cogs/xp/service.py
from __future__ import annotations

from typing import Dict, Any, Optional
from datetime import datetime, timezone, date

from utils.utils_json import load_json, save_json
from configs.config_files import ACTIVITY_DATA_FILE
from configs.config_files import VC_DAILY_LIMITS_FILE  # <-- NEW
from .weights import ACTIVITY_WEIGHTS

# --- CODE VARIABLE for daily VC limit (seconds/XP) ---
DAILY_VC_LIMIT: float = 200.0  # <--- change here if you ever need a different daily cap


def _ensure_user(data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    if user_id not in data:
        data[user_id] = {"xp": {}, "meta": {}}
    if "xp" not in data[user_id] or not isinstance(data[user_id]["xp"], dict):
        data[user_id]["xp"] = {}
    if "meta" not in data[user_id] or not isinstance(data[user_id]["meta"], dict):
        data[user_id]["meta"] = {}
    return data[user_id]


def _write(data: Dict[str, Any]) -> None:
    save_json(ACTIVITY_DATA_FILE, data)


def add_xp(user_id: int | str, amount: int | float, activity_type: str) -> int | float:
    if amount == 0:
        return 0
    uid = str(user_id)
    data = load_json(ACTIVITY_DATA_FILE, default_value={})
    u = _ensure_user(data, uid)

    current = float(u["xp"].get(activity_type, 0))
    new_val = current + float(amount)
    if new_val < 0:
        new_val = 0.0

    u["xp"][activity_type] = new_val
    _write(data)
    return new_val


def add_time(user_id: int | str, seconds: int | float, activity_type: str = "vc_seconds") -> float:
    return float(add_xp(user_id, float(seconds), activity_type))


# --- NEW: helpers for daily VC limit tracking in vc_limits.json ---

def _today_str() -> str:
    # Use UTC to match your use of datetime.utcnow() elsewhere
    return datetime.utcnow().date().isoformat()

def _load_vc_limits() -> Dict[str, Any]:
    return load_json(VC_DAILY_LIMITS_FILE, default_value={})

def _write_vc_limits(data: Dict[str, Any]) -> None:
    save_json(VC_DAILY_LIMITS_FILE, data)

def _get_current_vc_total(uid: str) -> float:
    data = load_json(ACTIVITY_DATA_FILE, default_value={})
    user = data.get(uid, {})
    xp = user.get("xp", {})
    return float(xp.get("vc_seconds", 0.0))


def _add_vc_with_daily_limit(user_id: int | str, seconds: int | float) -> float:
    """
    Enforce per-user daily limit:
      - Track today's gained amount in VC_DAILY_LIMITS_FILE.
      - If user is already >= DAILY_VC_LIMIT, do not update their VC XP.
      - Otherwise, add only up to the remaining allowance.
    Returns the user's new total vc_seconds (unchanged if blocked).
    """
    uid = str(user_id)
    amt = max(0.0, float(seconds))  # ignore negative/zero

    # load persisted daily counters
    limits = _load_vc_limits()
    today = _today_str()

    rec = limits.get(uid)
    if not rec or rec.get("date") != today:
        rec = {"date": today, "gained": 0.0}
        limits[uid] = rec

    gained = float(rec.get("gained", 0.0))

    # If already at/over the cap, block any update
    if gained >= DAILY_VC_LIMIT:
        # return current total without changing anything
        return _get_current_vc_total(uid)

    # Determine how much we are allowed to add today
    remaining = max(0.0, DAILY_VC_LIMIT - gained)
    to_add = min(amt, remaining)

    if to_add <= 0.0:
        return _get_current_vc_total(uid)

    # Perform the actual write to vc_seconds
    new_total = add_time(uid, to_add, "vc_seconds")

    # Update today's gained counter
    rec["gained"] = float(gained + to_add)
    limits[uid] = rec
    _write_vc_limits(limits)

    return float(new_total)


def set_meta(user_id: int | str, key: str, value: Any) -> None:
    uid = str(user_id)
    data = load_json(ACTIVITY_DATA_FILE, default_value={})
    u = _ensure_user(data, uid)
    u["meta"][key] = value
    _write(data)


def get_meta(user_id: int | str, key: str, default=None):
    uid = str(user_id)
    data = load_json(ACTIVITY_DATA_FILE, default_value={})
    u = _ensure_user(data, uid)
    return u["meta"].get(key, default)


def get_user_activity_breakdown(user_id: int | str) -> Dict[str, float]:
    uid = str(user_id)
    data = load_json(ACTIVITY_DATA_FILE, default_value={})
    u = data.get(uid)
    if not u or "xp" not in u:
        return {}
    return {k: float(v) for k, v in u["xp"].items()}


def get_total_xp(user_id: int | str, weights: Optional[Dict[str, float]] = None) -> float:
    w = ACTIVITY_WEIGHTS if weights is None else weights
    xp_map = get_user_activity_breakdown(user_id)
    total = 0.0
    for k, v in xp_map.items():
        total += float(v) * float(w.get(k, 1.0))
    return total


def update_xp(user_id: int | str, amount: int | float, activity_type: str = "messages"):
    """
    - If activity_type == "vc": treat amount as seconds and apply a per-user DAILY limit (DAILY_VC_LIMIT).
      We track today's gained VC in VC_DAILY_LIMITS_FILE. If a user is over the limit,
      we do not update their VC XP at all.
    - Else: increment the named bucket directly by `amount`.
    """
    if activity_type == "vc":
        new_val = _add_vc_with_daily_limit(user_id, amount)
    else:
        new_val = add_xp(user_id, amount, activity_type)

    # side-effects (unchanged) ...
    try:
        from bot import get_bot
        from configs.config_general import BOT_GUILD_ID
        from cogs.server.roles.assign import assign_role_based_on_xp
        from cogs.fun.nickname.service import refresh_suffix_if_present
        try:
            from configs.config_logging import xp_logger as _logger
        except Exception:
            _logger = None

        bot = get_bot()
        if not bot:
            if _logger:
                _logger.debug("update_xp: bot unavailable; skipping side-effects")
            return new_val

        guild = bot.get_guild(BOT_GUILD_ID)
        if not guild:
            if _logger:
                _logger.debug(f"update_xp: guild {BOT_GUILD_ID} not found; skipping side-effects")
            return new_val

        member = guild.get_member(int(user_id))
        if not member:
            if _logger:
                _logger.debug(f"update_xp: member {user_id} not in guild; skipping side-effects")
            return new_val

        bot.loop.create_task(assign_role_based_on_xp(member, guild))
        bot.loop.create_task(refresh_suffix_if_present(member))

        if _logger:
            _logger.info(f"User {user_id} +{amount} to '{activity_type}' (daily-limited for vc). New={new_val}")

    except Exception as e:
        try:
            from configs.config_logging import xp_logger as _logger
            _logger.exception(f"update_xp side-effects failed for user {user_id}: {e}")
        except Exception:
            pass

    return new_val
