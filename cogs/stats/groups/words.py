import discord

from configs.config_channels import BOTS_PLAYGROUND_CHANNEL_ID
from configs.config_files import WORDS_FILE
from utils.utils_json import load_json
from configs.helper import send_as_webhook


async def words(ctx, member):

    word_counts = load_json(WORDS_FILE)
    target = member or ctx.author
    user_id = str(target.id)

    if user_id not in word_counts or not word_counts[user_id]:
        await ctx.send(f"No word usage data found for {target.display_name}.")
        return

    sorted_words = sorted(
        word_counts[user_id].items(), key=lambda x: x[1], reverse=True
    )[:10]
    description = "\n".join(f"**{word}** — {count} times" for word, count in sorted_words)
    unique_count = len(word_counts[user_id])

    embed = discord.Embed(
        title=f"🗣️ Top Words Used by {target.display_name}",
        description=description,
        color=discord.Color.blue()
    )
    embed.add_field(name="🔢 Unique Words", value=str(unique_count), inline=False)

    await send_as_webhook(ctx, "words", embed=embed)
