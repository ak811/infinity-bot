# cogs/embeds/roles_and_channels.py
from __future__ import annotations
import discord
from configs.config_general import PUBIC_COMMANDS, BOT_GUILD_ID
from configs.config_roles import LOOT_AND_LEGENDS_PERKS, LOOT_AND_LEGENDS_ROLES

# Channels + message IDs
from configs.config_channels import ROLES_CHANNEL_ID, COMMANDS_CHANNEL_ID, CHANNELS_CHANNEL_ID

# Existing message IDs
COMMANDS_MESSAGE_ID = 1328591880660975669
PERKS_MESSAGE_ID = 1345970699193417760
CHANNELS_MESSAGE_ID = 1330358291880083569

# Excluded categories
EXCLUDED_CATEGORY_IDS = {
    1354054939634044959,
    1143301337547800626,
    1380689826793394236,
    1377353223370834061,
    1339433035183161405,
    1369452109862273125,
    1411939006886838353,
    1416793275964330204,
}

def format_command_embed() -> discord.Embed:
    embed = discord.Embed(title="🎉💰 Server Commands 💰🎉", color=discord.Color.gold())
    for category, commands in PUBIC_COMMANDS.items():
        value = "\n".join(commands)
        embed.add_field(name=category, value=value, inline=False)
    return embed

def format_perks_embed(bot: discord.Client) -> discord.Embed:
    role_xp = {role_id: min_xp for role_id, min_xp, _ in LOOT_AND_LEGENDS_ROLES}
    embed = discord.Embed(title="🏆 Server Roles & XP", color=discord.Color.blue())
    guild = bot.get_guild(BOT_GUILD_ID)

    if not guild:
        embed.description = "🙅 Guild not found."
        return embed

    description_lines = []
    for role_id, perks in LOOT_AND_LEGENDS_PERKS.items():
        mention = f"<@&{role_id}>"
        xp = role_xp.get(role_id)
        xp_str = f" — **{xp:,} XP**" if isinstance(xp, (int, float)) else ""
        perks_list = "\n".join(f"• {perk}" for perk in perks)
        description_lines.append(f"{mention}{xp_str}\n{perks_list}\n")

    embed.description = "\n".join(description_lines)
    return embed

def format_channels_embed(bot: discord.Client) -> discord.Embed:
    """List categories & channels (with topics), excluding some categories."""
    embed = discord.Embed(title="Server Categories & Channels", color=discord.Color.green())
    guild = bot.get_guild(BOT_GUILD_ID)

    if not guild:
        embed.description = "🙅 Guild not found."
        return embed

    categories = sorted(
        [c for c in guild.categories if c.id not in EXCLUDED_CATEGORY_IDS],
        key=lambda c: c.position,
    )

    lines: list[str] = []
    for category in categories:
        lines.append(f"**{category.name}**")
        for ch in sorted(category.channels, key=lambda c: getattr(c, "position", 0)):
            line = f" └─ <#{ch.id}>"
            if hasattr(ch, "topic") and ch.topic:
                topic = ch.topic.strip()
                line += f" — {topic}"
            lines.append(line)
        lines.append("")

    desc = "\n".join(lines).strip()
    if len(desc) > 4000:
        desc = desc[:3990].rstrip() + "\n…"

    embed.description = desc if desc else "No channels found."
    return embed

async def update_roles_and_commands_embeds(bot: discord.Client) -> None:
    commands_channel = bot.get_channel(COMMANDS_CHANNEL_ID)
    roles_channel = bot.get_channel(ROLES_CHANNEL_ID)
    channels_channel = bot.get_channel(CHANNELS_CHANNEL_ID)

    if commands_channel:
        cmd_msg = await commands_channel.fetch_message(COMMANDS_MESSAGE_ID)
        await cmd_msg.edit(embed=format_command_embed())

    if roles_channel:
        perks_msg = await roles_channel.fetch_message(PERKS_MESSAGE_ID)
        await perks_msg.edit(embed=format_perks_embed(bot))

    if channels_channel:
        channels_msg = await channels_channel.fetch_message(CHANNELS_MESSAGE_ID)
        await channels_msg.edit(embed=format_channels_embed(bot))

async def update_channels_embed_only(bot: discord.Client) -> None:
    channels_channel = bot.get_channel(CHANNELS_CHANNEL_ID)
    if not channels_channel:
        return
    msg = await channels_channel.fetch_message(CHANNELS_MESSAGE_ID)
    await msg.edit(embed=format_channels_embed(bot))
