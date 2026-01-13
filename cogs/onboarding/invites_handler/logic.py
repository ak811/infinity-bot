# cogs/invites_handler/logic.py
import logging
import discord
from cogs.onboarding.invites_handler.data import (
    invite_message_data,
    invite_rewards_given,
    save_invite_rewards,
)

from cogs.economy.diamond.service import update_diamonds

from configs.config_channels import LOGS_CHANNEL_ID
from configs.helper import send_as_webhook

# Map proxy inviter IDs to a main account if desired
PROXY_INVITE_MAPPING: dict[str, str] = {
    "927312859875119124": "377928910718894091",
    "1383932351125655680": "377928910718894091",
}

VANITY_ID = "vanity"  # bucket for vanity URL joins


async def handle_invite_reward(guild: discord.Guild, inviter: discord.abc.User, member: discord.Member):
    """
    Track + reward invites. Diamonds: +1 per every 5 new invites (cumulative).
    Vanity (or disboard bot id) is ignored for rewards.
    """
    original_id = str(inviter.id)
    actual_id = PROXY_INVITE_MAPPING.get(original_id, original_id)
    entry = invite_message_data.get(actual_id, {"count": 0, "msg_id": None, "invited_users": []})

    # no double-counting the same new member
    mid = str(member.id)
    if mid in entry["invited_users"]:
        return

    entry["invited_users"].append(mid)
    entry["count"] = int(entry.get("count", 0)) + 1
    invite_message_data[actual_id] = entry

    logging.info(f"[Invites] +1 for inviter {actual_id}: now {entry['count']} (added {member})")

    # ignore non-reward buckets
    if actual_id in [VANITY_ID, "302050872383242240"]:  # 3020… = Disboard bot
        return

    # Accumulate proxy totals under their main
    total = entry["count"]
    if actual_id == "377928910718894091":
        for proxy_id, main_id in PROXY_INVITE_MAPPING.items():
            if main_id == actual_id:
                total += invite_message_data.get(proxy_id, {}).get("count", 0)

    rewarded = int(invite_rewards_given.get(actual_id, 0))
    new_invites = total - rewarded
    new_diamonds = (new_invites // 5) * 1  # 1 diamond per 5 invites

    if new_diamonds > 0:
        invites_to_record = (new_invites // 5) * 5
        update_diamonds(actual_id, new_diamonds)
        invite_rewards_given[actual_id] = rewarded + invites_to_record
        save_invite_rewards()

        channel = guild.get_channel(LOGS_CHANNEL_ID)
        if channel:
            content = (
                f"💎 **<@{actual_id}>** has invited **{invites_to_record}** new member(s) "
                f"and earned **{new_diamonds} Diamond(s)**! 🎉"
            )
            await send_as_webhook(channel, "diamonds", content=content)
