# cogs/server/emojis/errors.py
from __future__ import annotations

class GuildOnlyError(RuntimeError): ...
class IntentsMissingError(RuntimeError): ...
class ItemNotFoundError(RuntimeError): ...

def user_message(exc: Exception) -> str:
    if isinstance(exc, GuildOnlyError):
        return "This command can only be used in a server."
    if isinstance(exc, IntentsMissingError):
        return "I need the **Emojis & Stickers** intent enabled to read server emojis/stickers."
    if isinstance(exc, ItemNotFoundError):
        return "I couldn’t find a matching emoji/sticker."
    return "Something went wrong while handling your request."
