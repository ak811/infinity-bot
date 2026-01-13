# cogs/close_circle/bff.py
import discord
from .logic import get_top_interaction_pairs
from .display import format_pairs_embed
from configs.helper import send_as_webhook

async def bff(ctx):
    top_pairs = get_top_interaction_pairs(ctx.guild, limit=10)
    if not top_pairs:
        return await ctx.send("No connections to show yet!")

    simplified = []
    for uid1, uid2, score, mutual_rel in top_pairs:
        m1 = ctx.guild.get_member(uid1) or await ctx.guild.fetch_member(uid1)
        m2 = ctx.guild.get_member(uid2) or await ctx.guild.fetch_member(uid2)
        if m1 and m2:
            simplified.append((m1, m2, score, mutual_rel))

    embed = format_pairs_embed(simplified, title="💖 Best Friends in the Server 💖", color=discord.Color.blurple())
    await send_as_webhook(ctx, "bff", embed=embed)
