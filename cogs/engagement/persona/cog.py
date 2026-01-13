# cogs/persona/cog.py
from __future__ import annotations

import logging
import discord
from discord.ext import commands
from openai import OpenAI

from configs.config_general import OPENAI_API_KEY
from configs.helper import send_as_webhook
from configs.config_pets import (
    HUMAN_PERSONAS,            # dict: pet_type -> { name, description, ... }
    HUMAN_PERSONAS_ROLE_IDS,   # dict: pet_type -> role_id
    HUMAN_PERSONAS_USER_IDS,   # dict: pet_type -> user_id
)

from .history import build_conversation_history


class PersonaCog(commands.Cog):
    """
    Responds as different human-like personas when mentioned or replied to.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log = logging.getLogger(__name__)
        # One OpenAI client for the whole cog
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    # ---- Listener ------------------------------------------------------------
    @commands.Cog.listener("on_message")
    async def on_message_listener(self, message: discord.Message):
        # Ignore DMs and bots
        if not isinstance(message.channel, discord.TextChannel) or message.author.bot:
            return

        # Try each configured persona
        for pet_type in HUMAN_PERSONAS.keys():
            try:
                handled = await self._maybe_handle_persona(message, pet_type)
                if handled:
                    return  # one persona per message
            except Exception as e:
                self.log.error(f"[Persona:{pet_type}] error: {e}", exc_info=True)
                # keep looping other personas if one fails

    # ---- Core handling -------------------------------------------------------
    async def _maybe_handle_persona(self, message: discord.Message, pet_type: str) -> bool:
        persona = HUMAN_PERSONAS.get(pet_type)
        if not persona:
            self.log.warning(f"[Persona] Unknown pet type: {pet_type}")
            return False

        persona_name: str = persona.get("name") or pet_type
        role_id = HUMAN_PERSONAS_ROLE_IDS.get(pet_type)
        persona_user_id = HUMAN_PERSONAS_USER_IDS.get(pet_type)

        # Was the persona mentioned directly (role or user) or replied to?
        mentioned_directly = any(getattr(role, "id", 0) == role_id for role in message.role_mentions) \
            or any(getattr(user, "id", 0) == persona_user_id for user in message.mentions)

        replying_to_persona = False
        if message.reference and message.reference.message_id:
            try:
                ref_msg = await message.channel.fetch_message(message.reference.message_id)
                if ref_msg.webhook_id and ref_msg.author and ref_msg.author.name == persona_name:
                    replying_to_persona = True
            except Exception as e:
                self.log.debug(f"[Persona:{pet_type}] Could not fetch reply reference: {e}")

        if not (mentioned_directly or replying_to_persona):
            return False

        # Build short history and ask the model
        try:
            history = await build_conversation_history(message, self.bot.user, persona_name)
            system_prompt = (
                f"You are {persona_name}, a unique character with a distinct personality. "
                f"Speak really casually and really briefly like a real human, with the style of: {persona.get('description', '')}"
            )

            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": system_prompt}, *history],
                max_tokens=50,
            )
            reply = (resp.choices[0].message.content or "").strip()
            if not reply:
                reply = "…"

            await send_as_webhook(message, pet_type=pet_type, content=reply)
            self.log.info(f"[{persona_name}] Replied.")
        except Exception as e:
            self.log.error(f"[Persona:{pet_type}] OpenAI/webhook error: {e}", exc_info=True)
            try:
                await message.channel.send(f"{persona_name} is busy right now. try later.")
            except Exception:
                pass

        return True


async def setup(bot: commands.Bot):
    await bot.add_cog(PersonaCog(bot))
