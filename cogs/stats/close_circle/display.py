# cogs/close_circle/display.py
import discord

def format_close_circle_embed(user: discord.Member, top_users, guild: discord.Guild):
    rank_emojis = ["❤️","💫","🌟","✨","🔥","🌸","💐","🌻","🌼","🪻","🌷","🌹","🥀","🍀","☀️","⭐","🌙","☁️","🌤️","🎉"]
    lines = []
    for i, (uid, score) in enumerate(top_users):
        other = guild.get_member(uid)
        if other:
            emoji = rank_emojis[i] if i < len(rank_emojis) else "💞"
            lines.append(f"{i + 1}. {emoji} **{other.display_name}** — **{score:.0f} pts**")
    desc = "\n".join(lines) if lines else "No interactions yet 😔"
    return discord.Embed(
        title=f"👥 Close Circle for {user.display_name}",
        description=desc,
        color=discord.Color.green(),
    )

def format_pairs_embed(top_pairs, title="🎉 Your Closest Connections! 🎉", color=discord.Color.magenta()):
    if not top_pairs:
        desc = "No connection pairs tracked yet 😢\nStart chatting to see your friendships bloom!"
    else:
        lines = []
        for i, (m1, m2, score, mutual_rel) in enumerate(top_pairs):
            lines.append(f"{i + 1}. **{m1.display_name}** ❤️ **{m2.display_name}** — **{mutual_rel * 100:.1f}%**")
        desc = "\n".join(lines)
    return discord.Embed(title=title, description=desc, color=color)
