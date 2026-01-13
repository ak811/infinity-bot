# cogs/transcription/tasks.py
from __future__ import annotations
from typing import Iterable, Awaitable, Optional

try:
    # Reuse your scheduler if present
    from events.helpers import schedule_tasks as _schedule_tasks
except Exception:
    _schedule_tasks = None

def schedule(coros: Iterable[Awaitable[object]]) -> Optional[None]:
    """
    Wrapper so the cog can call schedule() regardless of whether your
    global scheduler is available. Falls back to sequential awaits (handled by caller).
    """
    if _schedule_tasks:
        _schedule_tasks(tuple(coros))
