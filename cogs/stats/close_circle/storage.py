# cogs/close_circle/storage.py
import json
import os
from .state import DATA_FILE, interaction_scores, received_scores

def load_close_circle_data() -> None:
    if not DATA_FILE or not DATA_FILE.endswith(".json"):
        return
    try:
        if not os.path.exists(DATA_FILE):
            return
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception as e:
        print(f"[close_circle] Error loading data: {e}")
        return

    interaction_scores.clear()
    for user_str, others in (raw or {}).items():
        try:
            uid = int(user_str)
            scores_map = {int(k): v for k, v in others.items()}
            interaction_scores[uid] = scores_map
        except Exception:
            continue

    print(f"[close_circle] Loaded {len(interaction_scores)} users from {DATA_FILE}")
    build_directional_scores()

def save_close_circle_data() -> None:
    if not interaction_scores:
        print("[close_circle] No interaction data to save, skipping.")
        return
    to_save = {}
    for uid, scores in interaction_scores.items():
        if scores:
            filtered = {str(k): v for k, v in scores.items() if v}
            if filtered:
                to_save[str(uid)] = filtered
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
        os.replace(tmp, DATA_FILE)
    except Exception as e:
        print(f"[close_circle] Error saving data: {e}")

def build_directional_scores() -> None:
    received_scores.clear()
    for giver_id, targets in interaction_scores.items():
        for receiver_id, score in targets.items():
            received_scores[receiver_id][giver_id] = score
