# cogs/invites_handler/track_init.py
import logging
import discord
from cogs.onboarding.invites_handler.data import invite_code_data, save_invite_codes

async def initialize_invites_cache(bot: discord.Client):
    """
    Build bot.invites_cache[guild_id] = list[Invite] AND seed invite_code_data.
    Call once on_ready (per shard/process).
    """
    bot.invites_cache = {}

    for guild in bot.guilds:
        try:
            logging.info(f"[Invite Init] Fetching invites for {guild.name}")
            invites = await guild.invites()
            bot.invites_cache[guild.id] = invites

            for inv in invites:
                inviter = inv.inviter
                invite_code_data[inv.code] = {
                    "inviter_id": str(inviter.id) if inviter else "vanity",
                    "uses": inv.uses,
                }

            save_invite_codes()
        except discord.Forbidden:
            logging.warning(f"[Invite Init] Missing permissions for {guild.name}")
        except Exception as e:
            logging.error(f"[Invite Init Error] {guild.name}: {e}")
