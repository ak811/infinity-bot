# cogs/economy/orb/service.py
from __future__ import annotations
from utils.utils_json import load_json, save_json
from configs.config_files import USER_ORBS_FILE
from configs.config_logging import orbs_logger

def update_orbs(user_id: int | str, orb_amount: int, activity_type: str = "default"):
    if orb_amount == 0:
        return 0
    user_id = str(user_id)
    data = load_json(USER_ORBS_FILE, default_value={})
    data.setdefault(user_id, 0)

    if orb_amount > 0:
        data[user_id] += orb_amount
        save_json(USER_ORBS_FILE, data)
        orbs_logger.info(
            f"Added {orb_amount} orbs to user {user_id} for {activity_type}. Total now: {data[user_id]}."
        )
        return data[user_id]
    else:
        if data[user_id] < -orb_amount:
            orbs_logger.info(
                f"User {user_id} has insufficient orbs ({data[user_id]}) to deduct {-orb_amount}."
            )
            return False
        data[user_id] += orb_amount
        save_json(USER_ORBS_FILE, data)
        orbs_logger.info(
            f"Deducted {-orb_amount} orbs from user {user_id} for {activity_type}. Total now: {data[user_id]}."
        )
        return data[user_id]

def get_total_orbs(user_id: int | str) -> int:
    return load_json(USER_ORBS_FILE, default_value={}).get(str(user_id), 0)
