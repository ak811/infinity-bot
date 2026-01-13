from collections import Counter
import discord

from configs.config_files import (
    PING_COUNTS_FILE,
    REACTIONS_DETAIL_FILE,
    WORDS_FILE,
)
from utils.utils_json import load_json
from cogs.economy.coin.service import get_total_coins
from cogs.economy.orb.service import get_total_orbs
from cogs.economy.diamond.service import get_total_diamonds
from cogs.economy.star.service import get_total_stars

from configs.helper import send_as_webhook


async def show_full_stats(ctx):
    guild = ctx.guild
    members = [m for m in guild.members if not m.bot]

    total_coins = sum(get_total_coins(m.id) for m in members)
    total_orbs = sum(get_total_orbs(m.id) for m in members)
    total_diamonds = sum(get_total_diamonds(m.id) for m in members)
    total_stars = sum(get_total_stars(m.id) for m in members)  # ⬅️ NEW

    words_data = load_json(WORDS_FILE, default_value={})
    word_counter = Counter()
    for word_dict in words_data.values():
        word_counter.update(word_dict)
    most_used_word = word_counter.most_common(1)[0][0] if word_counter else "None"

    reactions_data = load_json(REACTIONS_DETAIL_FILE, default_value={})
    all_given_reactions = Counter()
    for user_data in reactions_data.values():
        all_given_reactions.update(user_data.get("given", {}))
    total_reactions = sum(all_given_reactions.values())
    most_used_reaction = (
        all_given_reactions.most_common(1)[0][0] if all_given_reactions else "None"
    )  # show just the emoji, not (emoji, count)

    ping_data = load_json(PING_COUNTS_FILE, default_value={})
    total_pings = sum(ping_data.values())

    embed = discord.Embed(title="📊 Server Stats", color=discord.Color.green())
    embed.add_field(name="🪙 Total Coins", value=total_coins, inline=True)
    embed.add_field(name="🔮 Total Orbs", value=total_orbs, inline=True)
    embed.add_field(name="⭐ Total Stars", value=total_stars, inline=True)          # ⬅️ NEW
    embed.add_field(name="💎 Total Diamonds", value=total_diamonds, inline=True)
    embed.add_field(name="🗨️ Most Used Word", value=most_used_word, inline=True)
    embed.add_field(name="🔁 Total Reactions", value=total_reactions, inline=True)
    embed.add_field(name="💬 Most Used Emoji", value=most_used_reaction, inline=True)
    embed.add_field(name="🔔 Total Pings", value=total_pings, inline=True)

    await send_as_webhook(ctx, "all_stats", embed=embed)
