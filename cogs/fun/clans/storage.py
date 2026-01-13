# cogs/clans/storage.py
import json
import os
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

DATA_DIR = "database"
CLANS_FILE = os.path.join(DATA_DIR, "clans.json")

# Schema:
# {
#   "clans": {
#       "<slug>": {
#           "name": "Pretty Name",
#           "icon": "🏴",
#           "motto": "string",
#           "leader_id": 123,
#           "created_at": "2025-09-02T00:00:00Z",
#           "members": [123, 456, ...]
#       }
#   },
#   "memberships": { "user_id_str": "<slug>" }
# }

_lock = asyncio.Lock()
_state: Dict[str, Any] = {"clans": {}, "memberships": {}}

def _ensure_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CLANS_FILE):
        with open(CLANS_FILE, "w", encoding="utf-8") as f:
            json.dump(_state, f, ensure_ascii=False, indent=2)

def _save():
    with open(CLANS_FILE, "w", encoding="utf-8") as f:
        json.dump(_state, f, ensure_ascii=False, indent=2)

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

async def load():
    _ensure_files()
    async with _lock:
        try:
            with open(CLANS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("clans", {})
            data.setdefault("memberships", {})
            _state.clear()
            _state.update(data)
        except Exception:
            _state.clear()
            _state.update({"clans": {}, "memberships": {}})
            _save()

def list_clans() -> Dict[str, Any]:
    return _state["clans"]

def get_clan(slug: str) -> Optional[Dict[str, Any]]:
    return _state["clans"].get(slug)

def get_user_clan_slug(user_id: int) -> Optional[str]:
    return _state["memberships"].get(str(user_id))

def is_user_in_clan(user_id: int) -> bool:
    return get_user_clan_slug(user_id) is not None

def create_clan(slug: str, name: str, leader_id: int, icon: str = "🏴", motto: str = "") -> Dict[str, Any]:
    if slug in _state["clans"]:
        raise ValueError("Clan already exists")
    clan = {
        "name": name,
        "icon": icon,
        "motto": motto,
        "leader_id": leader_id,
        "created_at": _now_iso(),
        "members": [leader_id],
    }
    _state["clans"][slug] = clan
    _state["memberships"][str(leader_id)] = slug
    _save()
    return clan

def join_clan(slug: str, user_id: int):
    clan = _state["clans"].get(slug)
    if not clan:
        raise ValueError("Clan not found")
    if user_id in clan["members"]:
        return
    clan["members"].append(user_id)
    _state["memberships"][str(user_id)] = slug
    _save()

def leave_clan(user_id: int):
    slug = _state["memberships"].get(str(user_id))
    if slug is None:
        return None
    clan = _state["clans"].get(slug)
    if not clan:
        _state["memberships"].pop(str(user_id), None)
        _save()
        return None

    if clan["leader_id"] == user_id and len(clan["members"]) > 1:
        raise PermissionError("Leader cannot leave while members remain; transfer or disband.")

    if user_id in clan["members"]:
        clan["members"].remove(user_id)
    _state["memberships"].pop(str(user_id), None)

    if not clan["members"]:
        _state["clans"].pop(slug, None)

    _save()
    return slug

def transfer_leader(slug: str, new_leader_id: int):
    clan = _state["clans"].get(slug)
    if not clan:
        raise ValueError("Clan not found")
    if new_leader_id not in clan["members"]:
        raise ValueError("New leader must be a clan member")
    clan["leader_id"] = new_leader_id
    _save()

def set_motto(slug: str, motto: str):
    clan = _state["clans"].get(slug)
    if not clan:
        raise ValueError("Clan not found")
    clan["motto"] = motto[:140]
    _save()

def set_icon(slug: str, icon: str):
    clan = _state["clans"].get(slug)
    if not clan:
        raise ValueError("Clan not found")
    clan["icon"] = icon[:4]
    _save()

def disband(slug: str):
    clan = _state["clans"].pop(slug, None)
    if clan:
        for uid in clan.get("members", []):
            _state["memberships"].pop(str(uid), None)
        _save()

def remove_member(slug: str, user_id: int):
    clan = _state["clans"].get(slug)
    if not clan:
        raise ValueError("Clan not found")
    if user_id in clan["members"]:
        clan["members"].remove(user_id)
        _state["memberships"].pop(str(user_id), None)
        _save()

def rename_clan(old_slug: str, new_slug: str, new_name: str):
    if new_slug in _state["clans"]:
        raise ValueError("Target clan name already exists")
    clan = _state["clans"].pop(old_slug, None)
    if not clan:
        raise ValueError("Clan not found")
    clan["name"] = new_name
    _state["clans"][new_slug] = clan
    for uid in clan["members"]:
        _state["memberships"][str(uid)] = new_slug
    _save()
