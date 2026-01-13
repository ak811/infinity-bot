# cogs/close_circle/logic.py
import discord
from typing import List, Tuple
from .state import interaction_scores

def get_top_interactions(user_id: int, guild: discord.Guild, limit: int = 10) -> List[Tuple[int, float]]:
    if user_id not in interaction_scores:
        return []
    results = []
    for uid, score in interaction_scores[user_id].items():
        member = guild.get_member(uid)
        if member and not member.bot:
            results.append((uid, score))
    return sorted(results, key=lambda x: x[1], reverse=True)[:limit]

def get_top_interaction_pairs(guild: discord.Guild, limit: int = 10) -> List[Tuple[int, int, float, float]]:
    raw: List[Tuple[int, int, float, float]] = []

    max_per_user = {uid: (max(others.values()) if others else 0) for uid, others in interaction_scores.items()}

    for uid1, others in interaction_scores.items():
        for uid2, score_ij in others.items():
            if uid1 >= uid2:
                continue
            score_ji = interaction_scores.get(uid2, {}).get(uid1, 0)
            combined = score_ij + score_ji
            if combined == 0:
                continue

            max1 = max_per_user.get(uid1, 0)
            max2 = max_per_user.get(uid2, 0)
            rel1 = score_ij / max1 if max1 else 0
            rel2 = score_ji / max2 if max2 else 0
            mutual_rel = (rel1 + rel2) / 2
            final_score = combined * mutual_rel

            m1 = guild.get_member(uid1)
            m2 = guild.get_member(uid2)
            if m1 and m2 and (not m1.bot) and (not m2.bot):
                raw.append((uid1, uid2, final_score, mutual_rel))

    raw.sort(key=lambda x: x[2], reverse=True)

    result: List[Tuple[int, int, float, float]] = []
    used = set()
    for u1, u2, fs, mr in raw:
        if u1 in used or u2 in used:
            continue
        result.append((u1, u2, fs, mr))
        used.update([u1, u2])
        if len(result) >= limit:
            break
    return result
