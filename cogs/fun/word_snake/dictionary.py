# cogs/word_snake/dictionary.py
from __future__ import annotations

import json
import os
import logging
from typing import Set

from configs.config_files import WORDS_DICTIONARY_FILE

class WordDictionary:
    """
    Lazy loads and caches the dictionary file; auto-reloads if the file mtime changes.
    """

    def __init__(self, path: str | None = None):
        self.path = path or WORDS_DICTIONARY_FILE
        self._cache: Set[str] | None = None
        self._mtime: float | None = None

    def _needs_reload(self) -> bool:
        try:
            mtime = os.path.getmtime(self.path)
        except Exception:
            return self._cache is None  # reload if we don't have anything
        return self._mtime is None or mtime != self._mtime

    def words(self) -> Set[str]:
        if self._needs_reload():
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Expecting a JSON array of words
                cached = {str(w).strip().lower() for w in data if str(w).strip()}
                self._cache = cached
                self._mtime = os.path.getmtime(self.path)
                logging.info(f"[WordSnake] Dictionary loaded with {len(self._cache)} words.")
            except Exception as e:
                logging.error(f"[WordSnake] Failed to load dictionary '{self.path}': {e}")
                # keep previous cache if present
                if self._cache is None:
                    self._cache = set()
        return self._cache or set()
