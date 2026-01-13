# cogs/economy/diamond/service.py
from __future__ import annotations
from utils.utils_json import load_json, save_json
from configs.config_files import USER_DIAMONDS_FILE
from configs.config_logging import diamonds_logger

def update_diamonds(user_id: int | str, diamond_amount: int, activity_type: str = "default"):
    if diamond_amount == 0:
        return 0
    user_id = str(user_id)
    data = load_json(USER_DIAMONDS_FILE, default_value={})
    data.setdefault(user_id, 0)

    if diamond_amount > 0:
        data[user_id] += diamond_amount
        save_json(USER_DIAMONDS_FILE, data)
        diamonds_logger.info(
            f"Added {diamond_amount} diamonds to user {user_id} for {activity_type}. Total now: {data[user_id]}."
        )
        return data[user_id]
    else:
        if data[user_id] < -diamond_amount:
            return False
        data[user_id] += diamond_amount
        save_json(USER_DIAMONDS_FILE, data)
        diamonds_logger.info(
            f"Deducted {-diamond_amount} diamonds from user {user_id} for {activity_type}. Total now: {data[user_id]}."
        )
        return data[user_id]

def get_total_diamonds(user_id: int | str) -> int:
    return load_json(USER_DIAMONDS_FILE, default_value={}).get(str(user_id), 0)
