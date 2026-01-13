# cogs/close_circle/cc.py
import discord
from .logic import get_top_interactions
from .display import format_close_circle_embed
from configs.helper import send_as_webhook

async def cc(ctx, member: discord.Member | None = None):
    target = member or ctx.author
    top_users = get_top_interactions(target.id, ctx.guild)
    if not top_users:
        await ctx.send(f"{target.display_name} doesn't have any tracked interactions yet 😢")
        return
    embed = format_close_circle_embed(target, top_users, ctx.guild)
    await send_as_webhook(ctx, "cc", embed=embed)
