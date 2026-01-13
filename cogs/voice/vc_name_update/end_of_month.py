# cogs/vc_name_update/end_of_month.py
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

SUNDAY = 6  # datetime.weekday(): Monday=0 ... Sunday=6


def _first_of_next_month(d: date) -> date:
    """Return the date for the first day of the next month (UTC calendar)."""
    y = d.year + (1 if d.month == 12 else 0)
    m = 1 if d.month == 12 else d.month + 1
    return date(y, m, 1)


def _last_of_month(d: date) -> date:
    """Return the last day-of-month date for d's month."""
    return _first_of_next_month(d) - timedelta(days=1)


def _reset_sunday_for_eom(eom: date) -> date:
    """
    From a month-end date, compute the 'reset Sunday':
    - If EOM is Sunday => that same day
    - Else => the first Sunday after EOM
    """
    delta = (SUNDAY - eom.weekday()) % 7  # 0 if Sun, 1 if Sat->Sun, 6 if Mon->next Sun
    return eom + timedelta(days=delta)


def next_reset_start(now_utc: datetime) -> datetime:
    """
    Compute the next reset moment (00:00 UTC of the 'reset Sunday' tied to a month-end):
    - If we're in the gap right after a month ends but before its 'reset Sunday',
      target that imminent Sunday.
    - Otherwise target the Sunday tied to the current month's end.
    """
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)

    today = now_utc.date()

    # Month-end that just passed (previous month)
    first_of_this_month = date(today.year, today.month, 1)
    eom_prev = first_of_this_month - timedelta(days=1)
    reset_prev = _reset_sunday_for_eom(eom_prev)
    reset_prev_dt = datetime(reset_prev.year, reset_prev.month, reset_prev.day, tzinfo=timezone.utc)

    if now_utc < reset_prev_dt:
        return reset_prev_dt

    # Otherwise, target the reset Sunday for the *current* month's end
    eom_curr = _last_of_month(today)
    reset_curr = _reset_sunday_for_eom(eom_curr)
    return datetime(reset_curr.year, reset_curr.month, reset_curr.day, tzinfo=timezone.utc)


def format_reset_label(now_utc: datetime) -> str:
    """
    Return a compact countdown like:
      'Reset of Month: 02d:03h'  (>=1 day left)
      'Reset of Month: 03h:25m'  (<1 day left)
    """
    target = next_reset_start(now_utc)
    rem = target - now_utc
    if rem.total_seconds() <= 0:
        return "Reset of Month: 00d:00h"

    s = int(rem.total_seconds())
    d, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, _ = divmod(s, 60)

    if d >= 1:
        return f"Reset of Month: {d}d:{h:02d}h"
    return f"Reset of Month: {h:02d}h:{m:02d}m"