# cogs/engagement/quiz_maker/stats.py
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class QuizResult:
    user_id: int
    guild_id: Optional[int]
    channel_id: int
    score: int
    total_questions: int
    percent: float
    difficulty_mode: str
    total_time: float
    average_time: float
    fastest_time: Optional[float]
    slowest_time: Optional[float]
    timestamp: float


class QuizStatsStore:
    """
    Tiny JSON backed stats store.

    This is intentionally simple. If you ever care about performance,
    you can replace this with a database like an adult.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or Path(__file__).with_name("quiz_stats.json")

    def _load_all(self) -> List[Dict[str, Any]]:
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return data
            return []
        except FileNotFoundError:
            return []
        except json.JSONDecodeError:
            return []

    def _save_all(self, items: List[Dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(items, f, indent=2)

    def add_result(self, result: QuizResult) -> None:
        items = self._load_all()
        items.append(result.__dict__)
        self._save_all(items)

    def get_user_stats(
        self, guild_id: Optional[int], user_id: int
    ) -> Optional[Dict[str, Any]]:
        items = self._load_all()
        user_items = [
            it
            for it in items
            if it.get("user_id") == user_id and it.get("guild_id") == guild_id
        ]
        if not user_items:
            return None

        quizzes_played = len(user_items)
        total_score = sum(it["score"] for it in user_items)
        total_questions = sum(it["total_questions"] for it in user_items)
        best_percent = max(it["percent"] for it in user_items)
        best_score = max(it["score"] for it in user_items)
        avg_percent = (
            total_score * 100.0 / total_questions if total_questions else 0.0
        )

        overall_fastest = min(
            (
                it.get("fastest_time")
                for it in user_items
                if it.get("fastest_time") is not None
            ),
            default=None,
        )

        return {
            "quizzes_played": quizzes_played,
            "total_score": total_score,
            "total_questions": total_questions,
            "best_percent": best_percent,
            "best_score": best_score,
            "avg_percent": avg_percent,
            "overall_fastest_time": overall_fastest,
        }

    def get_leaderboard(
        self, guild_id: Optional[int], limit: int = 10
    ) -> List[Dict[str, Any]]:
        items = self._load_all()
        guild_items = [it for it in items if it.get("guild_id") == guild_id]
        if not guild_items:
            return []

        agg: Dict[int, Dict[str, Any]] = {}
        for it in guild_items:
            uid = it["user_id"]
            entry = agg.setdefault(
                uid,
                {
                    "user_id": uid,
                    "total_score": 0,
                    "total_questions": 0,
                    "quizzes_played": 0,
                },
            )
            entry["total_score"] += it["score"]
            entry["total_questions"] += it["total_questions"]
            entry["quizzes_played"] += 1

        leaderboard: List[Dict[str, Any]] = []
        for uid, entry in agg.items():
            total_q = entry["total_questions"]
            avg_percent = (
                entry["total_score"] * 100.0 / total_q if total_q else 0.0
            )
            leaderboard.append(
                {
                    "user_id": uid,
                    "quizzes_played": entry["quizzes_played"],
                    "avg_percent": avg_percent,
                    "total_questions": total_q,
                    "total_score": entry["total_score"],
                }
            )

        leaderboard.sort(key=lambda e: e["avg_percent"], reverse=True)
        return leaderboard[:limit]
