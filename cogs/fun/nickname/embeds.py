# cogs/nickname/embeds.py
import discord

# A small, consistent look for all nickname-related embeds

def _member_color(member: discord.Member) -> discord.Color:
    # Prefer the top role color; fallback to blurple if default
    c = member.top_role.color if member.top_role else discord.Color.blurple()
    return c if c.value != 0 else discord.Color.blurple()

def nickname_help_embed(member: discord.Member, current_display: str) -> discord.Embed:
    """
    The main !nickname (no subcommand) embed: status + quick help.
    """
    embed = discord.Embed(
        title="✨ Nickname Helper",
        description="Self-service nickname tools powered by your XP & level.",
        color=_member_color(member),
    )
    embed.add_field(
        name="🧑‍💼 Current",
        value=f"`{current_display}`",
        inline=False,
    )
    embed.add_field(
        name="🛠️ Commands",
        value=(
            "• **`!nickname reset`** — 🧹 Remove XP/level suffix\n"
            "• **`!nickname addxp`** — 📈 Add **XP-only** part (e.g., `| 309/500 XP`)\n"
            "• **`!nickname addlevel`** — 🧭 Add **Level-only** part (e.g., `| L6`)\n"
            "• **`!nickname addboth`** — 🧩 Add **full** suffix (e.g., `| L6 • 309/500 XP`)"
        ),
        inline=False,
    )
    embed.set_footer(text="Tip: You can re-run these anytime — they auto-update to your current XP.")
    return embed

def success_embed(member: discord.Member, title: str, new_nick: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"✅ {title}",
        description=f"New nickname:\n`{new_nick}`",
        color=_member_color(member),
    )
    return embed

def info_embed(member: discord.Member, title: str, msg: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"ℹ️ {title}",
        description=msg,
        color=_member_color(member),
    )
    return embed

def error_embed(member: discord.Member, title: str, msg: str) -> discord.Embed:
    embed = discord.Embed(
        title=f"🚫 {title}",
        description=msg,
        color=discord.Color.red(),
    )
    return embed
