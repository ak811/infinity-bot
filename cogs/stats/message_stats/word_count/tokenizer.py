# cogs/message_stats/word_count/tokenizer.py
from __future__ import annotations

import re
from typing import Dict, Iterable, Set, Tuple

from configs.config_files import WORDS_FILE  # only to mirror original; not used directly

# -------------------------------------------------------------------
# Tunables (mirrors your original)
# -------------------------------------------------------------------
IGNORED_EXACT: Set[str] = {"com", "gif", "tenor", "discordapp", "webp"}
IGNORED_PREFIXES: Tuple[str, ...] = ("http",)
STOPWORDS: Set[str] = {
    "the","and","is","in","at","of","a","an","to","for","on","with",
    "by","from","as","that","this","these","those","it","be","are","was","were",
    "has","have","had","but","or","if","then","so","not","no","yes","i","you",
    "he","she","they","we","me","him","her","them","my","your","their","our","us"
}

# -------------------------------------------------------------------
# Regexes (precompiled for speed)
# -------------------------------------------------------------------
URL_RE = re.compile(r"""(?xi)
    (?:https?://|www\.)\S+
    |
    \b[^\s/:?#]+\.[a-z]{2,24}(?:[/:?#]\S*)?
""")

CDN_HOST_RE = re.compile(r"""(?xi)\b(
    (?:cdn\d*\.)?
    (?:giphy\.com|tenor\.com|twimg\.com|imgur\.com|
       discord(?:app)?\.com|discordcdn\.com|
       media\.[a-z0-9.-]+|images\.[a-z0-9.-]+|static\.[a-z0-9.-]+)
)\b""")

MEDIA_EXT_RE = re.compile(r"""(?i)\.(gif|gifv|webp|png|jpe?g|bmp|svg|mp4|mov|webm|heic|heif)(?:\b|$)""")
DISCORD_EMOJI_RE = re.compile(r"<a?:[A-Za-z0-9_~\-]+:\d+>")
SHORTCODE_EMOJI_RE = re.compile(r":[A-Za-z0-9_+\-]{1,64}:")
EMOJI_RE = re.compile(
    r"[\u200d\uFE0F\u2640-\u2642\u2600-\u26FF\u2700-\u27BF"
    r"\U0001F1E6-\U0001F1FF"
    r"\U0001F300-\U0001F5FF"
    r"\U0001F600-\U0001F64F"
    r"\U0001F680-\U0001F6FF"
    r"\U0001F700-\U0001F77F"
    r"\U0001F780-\U0001F7FF"
    r"\U0001F800-\U0001F8FF"
    r"\U0001F900-\U0001F9FF"
    r"\U0001FA00-\U0001FA6F"
    r"\U0001FA70-\U0001FAFF"
    r"\U0001FB00-\U0001FBFF]"
)
MENTION_OR_CHANNEL_RE = re.compile(r"(?:^|[\s.,;:!?()])[@#][A-Za-z0-9_./-]+")
FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
ANGLE_LINK_RE = re.compile(r"<[^>\s]+>")
TOKEN_RE = re.compile(r"\b[a-zA-Z']+\b")

def strip_noise(text: str) -> str:
    """Remove code, links, emoji, mentions/channels, and common media/CDN noise."""
    text = FENCED_CODE_RE.sub(" ", text)
    text = INLINE_CODE_RE.sub(" ", text)
    text = URL_RE.sub(" ", text)
    text = CDN_HOST_RE.sub(" ", text)
    text = ANGLE_LINK_RE.sub(" ", text)
    text = DISCORD_EMOJI_RE.sub(" ", text)
    text = SHORTCODE_EMOJI_RE.sub(" ", text)
    text = MENTION_OR_CHANNEL_RE.sub(" ", text)
    text = EMOJI_RE.sub(" ", text)
    return text

def is_noise_token(tok: str) -> bool:
    """Return True if token should be ignored."""
    if len(tok) == 1 and tok not in {"i", "u"}:
        return True
    if tok in STOPWORDS:
        return True
    if tok in IGNORED_EXACT or tok.startswith(IGNORED_PREFIXES):
        return True
    if any(ch.isdigit() for ch in tok):
        return True
    if MEDIA_EXT_RE.search(tok) or "/" in tok or "." in tok:
        return True
    return False

def extract_valid_words(message_content: str) -> list[str]:
    """
    - Skips leading bot commands (starting with '!').
    - Strips noise and tokenizes.
    - Applies all ignore rules.
    """
    if message_content.strip().startswith("!"):
        return []
    text = message_content.replace("\u200b", "").strip()
    text = strip_noise(text).lower()
    tokens = TOKEN_RE.findall(text)
    return [t for t in tokens if not is_noise_token(t)]
