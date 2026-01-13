from collections import Counter
import discord

from configs.config_channels import BOTS_PLAYGROUND_CHANNEL_ID
from configs.config_files import REACTIONS_DETAIL_FILE
from utils.utils_json import load_json
from configs.helper import send_as_webhook


async def reactions_entry(bot, ctx, args):

    if args and args[0].lower() == "top":
        await top_reactions(bot, ctx)
    else:
        member = ctx.message.mentions[0] if ctx.message.mentions else None
        await reactions(ctx, member)


async def reactions(ctx, member=None):
    target = member or ctx.author
    data = load_json(REACTIONS_DETAIL_FILE, default_value={})
    entry = data.get(str(target.id))

    if not entry:
        return await ctx.send(f"No reaction details found for {target.display_name}.")

    received = entry.get("received", {})
    given = entry.get("given", {})

    embed = discord.Embed(
        title=f"🔄 Reactions for {target.display_name}",
        color=discord.Color.purple()
    )

    for label, items in [("📥 Received", received), ("📤 Given", given)]:
        if items:
            top = sorted(items.items(), key=lambda x: x[1], reverse=True)[:5]
            lines = [f"{emoji} — {count}" for emoji, count in top]
            embed.add_field(name=label, value="\n".join(lines), inline=False)
        else:
            embed.add_field(name=label, value="None", inline=False)

    await send_as_webhook(ctx, "reactions", embed=embed)


async def top_reactions(bot, ctx):
    detail = load_json(REACTIONS_DETAIL_FILE, default_value={})
    top_given = []
    for uid, info in detail.items():
        given = info.get("given", {})
        if not given:
            continue
        emoji, cnt = max(given.items(), key=lambda x: x[1])
        top_given.append((uid, emoji, cnt))

    top_given.sort(key=lambda x: x[2], reverse=True)
    top_given = top_given[:10]

    if not top_given:
        return await ctx.send("No reactions given yet.")

    embed = discord.Embed(title="📤 Top Reactions Used", color=discord.Color.orange())
    lines = []
    for uid, emoji, cnt in top_given:
        user = await bot.fetch_user(int(uid))
        lines.append(f"{user.mention} — {emoji} ×{cnt}")
    embed.description = "\n".join(lines)
    await send_as_webhook(ctx, "top_reactions", embed=embed)
