# cogs/server/emojis/cache.py
from __future__ import annotations
import time
from typing import Callable, Dict, Tuple, TypeVar

T = TypeVar("T")
_store: Dict[str, Tuple[float, T]] = {}

def _now() -> float:
    return time.monotonic()

def make_key(kind: str, guild_id: int) -> str:
    return f"{kind}:{guild_id}"

def get_or_set(key: str, ttl_sec: int, loader: Callable[[], T]) -> T:
    hit = _store.get(key)
    if hit and _now() - hit[0] < ttl_sec:
        return hit[1]
    val = loader()
    _store[key] = (_now(), val)
    return val

def invalidate(kind: str, guild_id: int) -> None:
    _store.pop(make_key(kind, guild_id), None)
