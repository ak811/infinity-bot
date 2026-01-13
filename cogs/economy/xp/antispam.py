# cogs/xp/antispam.py
from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from typing import Deque, Tuple

from configs.config_logging import logging
from .service import update_xp

# --- Spam guard config ---
SPAM_WINDOW_SECONDS = 10
SPAM_MSG_THRESHOLD = 5
REPEAT_WINDOW_SECONDS = 60
REPEAT_SAME_THRESHOLD = 3
SHORT_BURST_LEN = 3
SHORT_BURST_THRESHOLD = 3

_user_msg_history: dict[int, Deque[Tuple[float, str]]] = defaultdict(lambda: deque(maxlen=50))

URL_RE = re.compile(
    r"""(?xi)
    (?:https?://|www\.)\S+
    |
    \b[^\s/:?#]+\.[a-z]{2,24}(?:[/:?#]\S*)?
    """
)
ANGLE_LINK_RE = re.compile(r"<[^>\s]+>")
NONLETTER_RE = re.compile(r"[^A-Za-z]+")
MEDIA_HOST_HINT = re.compile(
    r"""(?xi)
    (?:cdn\d*\.)?(?:giphy\.com|tenor\.com|twimg\.com|imgur\.com|
    discord(?:app)?\.com|discordcdn\.com|media\.[a-z0-9.-]+)
    """
)

def _is_spam_message(user_id: int, content: str, now: float) -> bool:
    dq = _user_msg_history[user_id]
    dq.append((now, content))
    longest = max(SPAM_WINDOW_SECONDS, REPEAT_WINDOW_SECONDS)
    while dq and (now - dq[0][0]) > longest:
        dq.popleft()

    recent_count = sum(1 for t, _ in dq if (now - t) <= SPAM_WINDOW_SECONDS)
    if recent_count >= SPAM_MSG_THRESHOLD:
        return True

    stripped = content.strip()
    if stripped:
        dup_count = sum(1 for t, c in dq if (now - t) <= REPEAT_WINDOW_SECONDS and c.strip() == stripped)
        if dup_count >= REPEAT_SAME_THRESHOLD:
            return True

    if len(stripped) < SHORT_BURST_LEN and recent_count >= SHORT_BURST_THRESHOLD:
        return True

    return False


def _is_link_or_media_like(content: str) -> bool:
    stripped = content.strip()
    if not stripped:
        return True

    without_angle = ANGLE_LINK_RE.sub(" ", stripped)
    without_urls = URL_RE.sub(" ", without_angle).strip()

    letters_only = NONLETTER_RE.sub("", without_urls)
    remaining_letters = len(letters_only)

    has_url = bool(URL_RE.search(stripped))
    media_host = bool(MEDIA_HOST_HINT.search(stripped))

    if (has_url and remaining_letters < 8) or media_host:
        return True
    return False


def _text_letter_length(s: str) -> int:
    return len(NONLETTER_RE.sub("", s))


def handle_xp_with_antispam(user_id: int, content: str) -> None:
    """
    Checks if message is spammy; if not, calculates XP and updates.
    - Pure links/media/gifs/files => 1 XP
    - Empty/attachments-only => 1 XP
    - Regular text => XP based on alphabetic characters only (not URL length)
    """
    now = time.monotonic()
    if _is_spam_message(user_id, content, now):
        logging.info(f"[SpamGuard] Suppressed XP for user {user_id}")
        return

    if _is_link_or_media_like(content):
        xp = 1
        reason = "link/media"
    else:
        text_len = _text_letter_length(content)
        xp = 0 if text_len <= 5 else min(7, max(1, text_len // 7))
        reason = "message length"

    update_xp(user_id, xp, reason)
