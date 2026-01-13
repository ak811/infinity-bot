# pycord/queue/state.py

import typing as t

# vc_id -> {
#   "message_id": int,
#   "user_ids": list[int],
#   "channel_id": int,
#   "hook": discord.Webhook (optional)
# }
queue_state: dict[int, dict[str, t.Any]] = {}
