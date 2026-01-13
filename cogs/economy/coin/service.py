# cogs/economy/coin/service.py
from __future__ import annotations
from utils.utils_json import load_json, save_json
from configs.config_files import USER_COINS_FILE
from configs.config_logging import coins_logger

def update_coins(user_id: int | str, coin_amount: int, activity_type: str = "default"):
    if coin_amount == 0:
        return 0
    user_id = str(user_id)
    data = load_json(USER_COINS_FILE, default_value={})
    data.setdefault(user_id, 0)

    if coin_amount > 0:
        data[user_id] += coin_amount
        save_json(USER_COINS_FILE, data)
        coins_logger.info(
            f"Added  🪙 {coin_amount} to user {user_id} for {activity_type}. Total now: {data[user_id]}."
        )
        return data[user_id]
    else:
        if data[user_id] < -coin_amount:
            coins_logger.info(
                f"User {user_id} has insufficient coins ({data[user_id]}) to deduct {-coin_amount}."
            )
            return False
        data[user_id] += coin_amount
        save_json(USER_COINS_FILE, data)
        coins_logger.info(
            f"Deducted  🪙 {-coin_amount} from user {user_id} for {activity_type}. Total now: {data[user_id]}."
        )
        return data[user_id]

def get_total_coins(user_id: int | str) -> int:
    return load_json(USER_COINS_FILE, default_value={}).get(str(user_id), 0)
