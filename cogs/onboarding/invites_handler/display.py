# cogs/invites_handler/display.py
import discord

def format_invite_leaderboard(sorted_invites, guild: discord.Guild) -> discord.Embed:
    lines = []
    for inviter_id, data in sorted_invites[:10]:
        if inviter_id == "vanity":
            name = "Server Public Invite"
        else:
            member = guild.get_member(int(inviter_id))
            name = member.display_name if member else f"<@{inviter_id}>"
        lines.append(f"👤 **{name}** — {data.get('count', 0)} invite(s)")

    return discord.Embed(
        title="🏆 Top Inviters",
        description="\n".join(lines) if lines else "No invites tracked yet.",
        color=discord.Color.gold(),
    )
