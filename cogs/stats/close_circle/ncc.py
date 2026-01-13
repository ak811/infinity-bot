# cogs/close_circle/ncc.py
import discord
from .state import interaction_scores
from configs.helper import send_as_webhook

def _total_given(uid: int) -> int:
    return int(sum(interaction_scores.get(uid, {}).values()))

def _total_received(uid: int) -> int:
    total = 0
    for other_id, out_map in interaction_scores.items():
        if other_id == uid:
            continue
        total += int(out_map.get(uid, 0))
    return total

async def ncc(ctx, member: discord.Member | None = None):
    target = member or ctx.author
    gid = ctx.guild
    tid = target.id

    MIN_ACTIVE = 20
    MAX_ATTENTION = 0.15  # (kept for reference; current scoring uses zero-attention only)
    LIMIT = 5

    results = []
    for other in gid.members:
        if other.bot or other.id == tid:
            continue

        given_other = _total_given(other.id)
        recv_other = _total_received(other.id)
        total_active = given_other + recv_other
        if total_active < MIN_ACTIVE:
            continue

        toward_you = int(interaction_scores.get(other.id, {}).get(tid, 0)) + int(interaction_scores.get(tid, {}).get(other.id, 0))
        if toward_you > 0:
            continue

        attention_ratio = 0.0
        score = (1.0 - attention_ratio) * total_active
        results.append((other, score, toward_you, total_active, attention_ratio))

    if not results:
        return await send_as_webhook(ctx, "ncc", content="No one is really ignoring you 😄")

    results.sort(key=lambda x: x[1], reverse=True)
    top_results = results[:LIMIT]
    top_results.sort(key=lambda x: x[4])

    emojis = ["👿","💢","😤","🤬","☠️","👺","😠","👎","🙄","😒"]
    lines = []
    for idx, (other, score, toward, total, ratio) in enumerate(top_results, start=1):
        emoji = emojis[(idx - 1) % len(emojis)]
        lines.append(f"**#{idx}** {emoji} **{other.display_name}** — 🎯 `{toward}` attention toward you / `{total}` total (*{ratio*100:.1f}%*)")

    embed = discord.Embed(
        title=f"💔 {target.display_name}'s enemies 😡",
        description="\n".join(lines),
        color=discord.Color.red(),
    )
    embed.set_footer(text="They’re active… just not with you 🥶")
    await send_as_webhook(ctx, "ncc", embed=embed)
