# cogs/close_circle/nbff.py
import math
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

def _top_partner(uid: int) -> int | None:
    row = interaction_scores.get(uid, {})
    if not row:
        return None
    return max(row.items(), key=lambda kv: kv[1])[0] if row else None

async def nbff(ctx):
    guild = ctx.guild
    MIN_ACTIVE_USER = 30
    LIMIT = 10

    members = [m for m in guild.members if not m.bot]
    id_set = {m.id for m in members}

    totals = {m.id: (_total_given(m.id) + _total_received(m.id)) for m in members}
    tops = {m.id: _top_partner(m.id) for m in members}

    pairs = []
    ids = sorted(id_set)
    for i, uid1 in enumerate(ids):
        act1 = totals.get(uid1, 0)
        if act1 < MIN_ACTIVE_USER:
            continue
        for uid2 in ids[i+1:]:
            act2 = totals.get(uid2, 0)
            if act2 < MIN_ACTIVE_USER:
                continue
            m12 = int(interaction_scores.get(uid1, {}).get(uid2, 0))
            m21 = int(interaction_scores.get(uid2, {}).get(uid1, 0))
            mutual = m12 + m21
            if mutual != 0:
                continue
            if tops.get(uid1) == uid2 or tops.get(uid2) == uid1:
                continue
            score = math.sqrt(min(act1, act2))
            pairs.append((uid1, uid2, score, float(mutual), 0.0))

    if not pairs:
        return await send_as_webhook(ctx, "nbff", content="No perfectly separate ‘stranger’ pairs found 😄")

    pairs.sort(key=lambda x: x[2], reverse=True)
    used = set()
    final = []
    for u1, u2, score, mutual, share in pairs:
        if u1 in used or u2 in used:
            continue
        final.append((u1, u2, score, mutual, share))
        used.add(u1); used.add(u2)
        if len(final) >= LIMIT:
            break

    emojis = ["🧊","👻","🥶","🤐","😵","😿","😑","🤷","🪓","🧱"]
    lines = []
    for idx, (u1, u2, score, mutual, share) in enumerate(final, start=1):
        m1 = guild.get_member(u1)
        m2 = guild.get_member(u2)
        if not m1 or not m2:
            continue
        emoji = emojis[(idx - 1) % len(emojis)]
        lines.append(f"**#{idx}** **{m1.display_name}** {emoji} **{m2.display_name}** — *0 mutual pts* • both very active")

    embed = discord.Embed(
        title="🧊 Perfect Strangers in the Server",
        description="\n".join(lines) if lines else "No qualifying pairs found 😄",
        color=discord.Color.blue(),
    )
    embed.set_footer(text="They’re active… just never with each other")
    await send_as_webhook(ctx, "nbff", embed=embed)
