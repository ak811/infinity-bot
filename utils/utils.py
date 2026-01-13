from utils.utils_json import load_json, save_json
from cogs.economy.coin.service import get_total_coins
from cogs.economy.orb.service import get_total_orbs
from utils.utils_json import load_json
from configs.config_files import USER_DIAMONDS_FILE

# Third-Party Libraries
import discord
# Project-Specific Modules
from configs.config_logging import logging
from configs.config_general import BOT_GUILD_ID
from configs.config_channels import (
    BOT_PLAYGROUND_CHANNEL_ID
)
from configs.config_channels import LOGS_CHANNEL_ID
from openai import OpenAI

# Initialize OpenAI client (needed for GPT emoji functions)
from configs.config_general import OPENAI_API_KEY
client = OpenAI(api_key=OPENAI_API_KEY)

from bot import get_bot
bot = get_bot()

async def log_coin_transaction(ctx, sender: discord.Member, receiver: discord.Member, coins: int, status: str):
    """
    Logs a coin transaction to the staff logs channel.
    """
    channel = ctx.guild.get_channel(LOGS_CHANNEL_ID)
    if channel:
        color = discord.Color.green() if status == "approved" else discord.Color.red() if status == "declined" else discord.Color.orange()
        embed = discord.Embed(
            title="🪙 Transaction",
            description=(
                f"**Sender:** {sender.mention} ({sender.id})\n"
                f"**Receiver:** {receiver.mention} ({receiver.id})\n"
                f"**Amount:**  🪙 {coins}\n"
                f"**Status:** {status.capitalize()}"
            ),
            color=color,
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Initiated by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        await channel.send(embed=embed)

def increment_json_count(filepath, user_id: int):
    data = load_json(filepath)
    user_id = str(user_id)
    data[user_id] = data.get(user_id, 0) + 1
    save_json(filepath, data)

def increment_reaction_detail(filename: str, user_id: int, bucket: str, key: str, amount: int = 1):
    """
    In filename (a JSON of the form { user_id: { 'received': {}, 'given': {} }, ... }),
    increment data[user_id][bucket][key] by `amount`, initializing as needed.
    """
    if bucket not in ("received", "given"):
        raise ValueError("bucket must be 'received' or 'given'")

    data = load_json(filename, default_value={})
    uid = str(user_id)

    # init user entry
    if uid not in data:
        data[uid] = {"received": {}, "given": {}}

    # increment
    key = str(key)
    data[uid][bucket][key] = data[uid][bucket].get(key, 0) + amount

    save_json(filename, data)
