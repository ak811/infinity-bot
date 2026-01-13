# cogs/economy/star/service.py
from __future__ import annotations
from utils.utils_json import load_json, save_json
from configs.config_files import USER_STARS_FILE
from configs.config_logging import stars_logger

def update_stars(user_id: int | str, star_amount: int, activity_type: str = "default"):
    if star_amount == 0:
        return 0
    user_id = str(user_id)
    data = load_json(USER_STARS_FILE, default_value={})
    data.setdefault(user_id, 0)

    if star_amount > 0:
        data[user_id] += star_amount
        save_json(USER_STARS_FILE, data)
        stars_logger.info(
            f"Added ⭐ {star_amount} to user {user_id} for {activity_type}. Total now: {data[user_id]}."
        )
        return data[user_id]
    else:
        if data[user_id] < -star_amount:
            stars_logger.info(
                f"User {user_id} has insufficient stars ({data[user_id]}) to deduct {-star_amount}."
            )
            return False
        data[user_id] += star_amount
        save_json(USER_STARS_FILE, data)
        stars_logger.info(
            f"Deducted ⭐ {-star_amount} stars from user {user_id} for {activity_type}. Total now: {data[user_id]}."
        )
        return data[user_id]

def get_total_stars(user_id: int | str) -> int:
    return load_json(USER_STARS_FILE, default_value={}).get(str(user_id), 0)
