# cogs/reactions/donations.py
from __future__ import annotations
import discord
import logging

from configs.config_channels import LOGS_CHANNEL_ID

from cogs.economy.coin.service import update_coins, get_total_coins
from cogs.economy.orb.service import update_orbs, get_total_orbs
from cogs.economy.star.service import update_stars, get_total_stars

from configs.config_general import COIN_EMOJI, ORB_EMOJI, STAR_EMOJI
from configs.helper import send_as_webhook

# Shared with the listener to ignore mirrored removals
ignored_reactions: set[tuple[int, int, str]] = set()

def _resolve_ledger(emoji_str: str):
    if emoji_str == COIN_EMOJI:
        return get_total_coins, update_coins, "coin", COIN_EMOJI
    if emoji_str == ORB_EMOJI:
        return get_total_orbs, update_orbs, "orb", ORB_EMOJI
    return get_total_stars, update_stars, "star", STAR_EMOJI

async def handle_donation_reaction(
    payload: discord.RawReactionActionEvent,
    message: discord.Message,
    bot: discord.Client,
    emoji_str: str,
    action: str,
) -> bool:
    donor_id = payload.user_id
    recipient_id = message.author.id
    message_id = payload.message_id

    logging.info(f"[Donate] Handling {action} for {emoji_str} on msg={message_id} by user={donor_id}")

    get_balance, update_func, emoji_name, emoji_icon = _resolve_ledger(emoji_str)
    key = (message_id, donor_id, emoji_str)

    # Self reaction → remove and ignore
    if message.author.bot or donor_id == recipient_id:
        logging.info("[Donate] Self-reaction detected; removing.")
        if action == "add":
            try:
                ignored_reactions.add(key)
                await message.remove_reaction(emoji_str, discord.Object(id=donor_id))
            except Exception as e:
                logging.warning(f"[Donate] Failed to remove self-reaction: {e}")
        return True

    if action == "add":
        donor_balance = get_balance(donor_id)
        if donor_balance < 1:
            logging.info(f"[Donate] Insufficient balance for {donor_id}; removing reaction.")
            try:
                ignored_reactions.add(key)
                await message.remove_reaction(emoji_str, discord.Object(id=donor_id))
            except Exception as e:
                logging.warning(f"[Donate] Failed to remove reaction: {e}")
            return True

        update_func(donor_id, -1, f"donate_{emoji_name}")
        update_func(recipient_id, 1, f"receive_{emoji_name}")

        logs_channel = bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            embed = discord.Embed(
                description=(
                    f"{emoji_icon} <@{donor_id}> **donated 1 {emoji_name}** to <@{recipient_id}>'s "
                    f"[message]({message.jump_url}) in <#{message.channel.id}>"
                ),
                color=discord.Color.green(),
            )
            await send_as_webhook(logs_channel, "donation", embed=embed)
        return True

    if action == "remove":
        update_func(donor_id, 1, f"undo_donate_{emoji_name}")
        update_func(recipient_id, -1, f"undo_receive_{emoji_name}")

        logs_channel = bot.get_channel(LOGS_CHANNEL_ID)
        if logs_channel:
            embed = discord.Embed(
                description=(
                    f"{emoji_icon} <@{donor_id}> **removed their {emoji_name} donation** from <@{recipient_id}>'s "
                    f"[message]({message.jump_url}) in <#{message.channel.id}>"
                ),
                color=discord.Color.red(),
            )
            await send_as_webhook(logs_channel, "donation", embed=embed)
        return True

    return False
