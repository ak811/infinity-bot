# cogs/invites_handler/data.py

import logging
from utils.utils_json import load_json, save_json

INVITE_DATA_FILE = "database/invite_data.json"
INVITE_CODE_FILE = "database/invite_codes.json"
INVITE_REWARDS_FILE = "database/invite_rewards.json"

# inviter_id → {count, invited_users: [user_ids], msg_id?}
invite_message_data: dict[str, dict] = {}

# invite_code → {inviter_id, uses}
invite_code_data: dict[str, dict] = {}

# inviter_id → int (how many invites already rewarded)
invite_rewards_given: dict[str, int] = {}


def load_invite_data():
    logging.info("[Invites] Loading invite message data")
    invite_message_data.update(load_json(INVITE_DATA_FILE, {}))


def save_invite_data():
    save_json(INVITE_DATA_FILE, invite_message_data)


def load_invite_codes():
    logging.info("[Invites] Loading invite code data")
    invite_code_data.update(load_json(INVITE_CODE_FILE, {}))


def save_invite_codes():
    save_json(INVITE_CODE_FILE, invite_code_data)


def load_invite_rewards():
    invite_rewards_given.update(load_json(INVITE_REWARDS_FILE, {}))


def save_invite_rewards():
    save_json(INVITE_REWARDS_FILE, invite_rewards_given)
