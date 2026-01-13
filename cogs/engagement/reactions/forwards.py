# cogs/reactions/forwards.py
from __future__ import annotations
import discord
import logging
from configs.config_general import (
    FORWARD_EMOJI,
    AUTHOR_EMOJI,
    CHANNEL_EMOJI,
    LINK_EMOJI,
    MESSAGE_EMOJI,
    PAPERCLIP_EMOJI,
    EMBED_EMOJI,
)

async def forward_message_to_dm(
    payload: discord.RawReactionActionEvent,
    message: discord.Message,
    bot: discord.Client,
) -> bool:
    if str(payload.emoji) != FORWARD_EMOJI:
        return False

    user = bot.get_user(payload.user_id)
    if not user:
        logging.debug(f"[DMForward] User {payload.user_id} not found")
        return False

    try:
        if not (message.content or message.attachments or message.embeds):
            logging.debug(f"[DMForward] Message {message.id} has nothing to forward")
            return True

        dm = await user.create_dm()

        author_mention = message.author.mention
        channel_mention = f"<#{message.channel.id}>"
        jump_link = f"[Click here to view the original message]({message.jump_url})"

        header = (
            f"## **{FORWARD_EMOJI} Saved Message**\n"
            f"{AUTHOR_EMOJI} **Author:** {author_mention}\n"
            f"{CHANNEL_EMOJI} **Channel:** {channel_mention}\n"
            f"{LINK_EMOJI} {jump_link}"
        )

        content = message.content.strip() if message.content else ""
        body = f"{header}\n\n{MESSAGE_EMOJI} **Message:**\n{content}" if content else header

        files = [await attachment.to_file() for attachment in message.attachments]
        if files:
            body += f"\n\n{PAPERCLIP_EMOJI} **Attachments included.**"

        if message.embeds:
            body += f"\n{EMBED_EMOJI} **Embed(s) included below.**"

        await dm.send(content=body, embeds=message.embeds, files=files)
        logging.info(f"[DMForward] Forwarded message {message.id} to {user}")
        return True

    except discord.Forbidden:
        logging.warning(f"[DMForward] Cannot send DM to {user.name}")
    except Exception as e:
        logging.error(f"[DMForward] Failed to forward message {message.id} to {user.name}: {e}")

    return True  # still handled, even if it failed
