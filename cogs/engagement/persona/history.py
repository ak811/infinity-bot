# cogs/persona/history.py
from __future__ import annotations

import logging
import discord

from configs.config_pets import HUMAN_PERSONAS_ROLE_IDS

async def build_conversation_history(
    message: discord.Message,
    bot_user: discord.User | discord.ClientUser,
    persona_name: str,
    limit: int = 10,
) -> list[dict]:
    """
    Collect a short, relevant context window around the persona.
    Includes recent messages to/from the persona and the user’s current prompt.
    """
    logging.info(f"[{persona_name}] Building conversation history...")

    relevant: list[dict] = []

    async for msg in message.channel.history(limit=limit):
        if msg.id == message.id:
            continue

        is_from_persona = (msg.webhook_id is not None) or (msg.author.id == bot_user.id) or (msg.author.name == persona_name)
        is_to_persona = (
            any(role.id == HUMAN_PERSONAS_ROLE_IDS.get(persona_name.lower()) for role in msg.role_mentions)
            or (msg.reference and msg.reference.message_id == message.id)
            or (msg.reference and message.reference and msg.reference.message_id == message.reference.message_id)
        )

        if is_to_persona or is_from_persona:
            role = "assistant" if is_from_persona else "user"
            content = (msg.content or "").strip()
            if content:
                relevant.append({"role": role, "content": content})

        if len(relevant) >= 10:
            break

    relevant.reverse()
    # Current user message at the end
    relevant.append({"role": "user", "content": (message.content or '').strip()})
    logging.info(f"[{persona_name}] History length used: {len(relevant)})")
    return relevant
