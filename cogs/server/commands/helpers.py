from __future__ import annotations
import discord
from discord.ext import commands
from typing import Dict, List, Iterable, Tuple

# ---------- filters ----------
def _is_public_command(cmd: commands.Command) -> bool:
    # exclude hidden/disabled, commands explicitly marked sudo, and names starting with 'sudo'
    name = (cmd.qualified_name or "").lower()
    return (
        cmd.enabled
        and not getattr(cmd, "hidden", False)
        and not getattr(cmd, "is_sudo", False)
        and not name.startswith("sudo")
    )

def _is_sudo_like(cmd: commands.Command) -> bool:
    # list anything that starts with 'sudo' (aliases and subcommands show under their qualified_name anyway)
    name = (cmd.qualified_name or "").lower()
    return cmd.enabled and name.startswith("sudo")

# ---------- formatting ----------
MAX_FIELDS_PER_EMBED = 25
MAX_FIELD_VALUE = 1024  # Discord cap per field value

def _fmt_cmd_name(cmd: commands.Command, prefix: str) -> str:
    # Only show command tokens (no descriptions, no cogs, no aliases)
    return f"`{prefix}{cmd.qualified_name}`"

def _chunk_text(items: List[str], sep: str = " • ", max_len: int = MAX_FIELD_VALUE) -> List[str]:
    """Pack items into chunks that fit under max_len using 'sep'."""
    chunks: List[str] = []
    cur: List[str] = []
    cur_len = 0
    for it in items:
        add_len = (len(sep) if cur else 0) + len(it)
        if cur and cur_len + add_len > max_len:
            chunks.append(sep.join(cur))
            cur, cur_len = [it], len(it)
        else:
            cur.append(it)
            cur_len += add_len
    if cur:
        chunks.append(sep.join(cur))
    return chunks

def _build_embeds_from_fields(
    title: str,
    description: str,
    fields: List[Tuple[str, str]],
    *,
    footer: str | None = None,
    color: discord.Color = discord.Color.blurple(),
) -> List[discord.Embed]:
    """Build paged embeds from a prebuilt list of (name, value) fields."""
    embeds: List[discord.Embed] = []
    for i in range(0, len(fields), MAX_FIELDS_PER_EMBED):
        page_fields = fields[i : i + MAX_FIELDS_PER_EMBED]
        embed = discord.Embed(title=title, description=description, color=color)
        for name, value in page_fields:
            embed.add_field(name=name, value=value or "_None_", inline=False)
        if footer:
            embed.set_footer(text=footer)
        embeds.append(embed)

    if not embeds:
        embed = discord.Embed(title=title, description="No commands found.", color=color)
        if footer:
            embed.set_footer(text=footer)
        embeds.append(embed)
    return embeds

# ---------- categorization ----------
# PUBLIC categories (ordered)
_PUBLIC_CATEGORY_TITLES: List[str] = [
    "👤 Profile & Social",
    "🪙 Currency",
    "💎 Inventory",
    "🛍️ Shop & Bank",
    "📈 Stats & Leaderboards",
    "📨 Invites & Pings",
    "🗂️ Channels & Roles",
    "✉️ Direct Messages",
    "🎮 Games & Fun",
    "🧭 Help & Info",
    "🛠️ Utilities",
    "📦 Misc",
]

# Map base public command -> category title
_PUBLIC_CATEGORY_MAP: Dict[str, str] = {
    # Profile & Social
    "profile": "👤 Profile & Social",
    "avatar": "👤 Profile & Social",
    "nickname": "👤 Profile & Social",
    "compliment": "👤 Profile & Social",
    "clan": "👤 Profile & Social",
    "clans": "👤 Profile & Social",
    "confirmation": "👤 Profile & Social",  # keep here so it's easy to find
    "owl": "👤 Profile & Social",

    # Currency
    "coins": "🪙 Currency",
    "send_coins": "🪙 Currency",
    "dollars": "🪙 Currency",

    # Inventory
    "orbs": "💎 Inventory",
    "stars": "💎 Inventory",
    "diamonds": "💎 Inventory",

    # Shop & Bank
    "shop": "🛍️ Shop & Bank",
    "refresh_shops": "🛍️ Shop & Bank",
    "bank": "🛍️ Shop & Bank",

    # Stats & Leaderboards
    "leaderboard": "📈 Stats & Leaderboards",
    "stats": "📈 Stats & Leaderboards",
    "xp": "📈 Stats & Leaderboards",

    # Invites & Pings
    "invites": "📨 Invites & Pings",
    "pings": "📨 Invites & Pings",
    "top_pings": "📨 Invites & Pings",

    # Channels & Roles
    "channels": "🗂️ Channels & Roles",
    "roles": "🗂️ Channels & Roles",

    # Direct Messages (public)
    "send_dm": "✉️ Direct Messages",

    # Games & Fun
    "bet": "🎮 Games & Fun",
    "fortune": "🎮 Games & Fun",
    "topic": "🎮 Games & Fun",
    "dice": "🎮 Games & Fun",
    "coinflip": "🎮 Games & Fun",
    "spin": "🎮 Games & Fun",

    # Help & Info
    "help": "🧭 Help & Info",
    "faq": "🧭 Help & Info",
    "alias": "🧭 Help & Info",
    "aliases": "🧭 Help & Info",
    "all": "🧭 Help & Info",
    "birthdays": "🧭 Help & Info",
    "reactions": "🧭 Help & Info",
    "reactions_top": "🧭 Help & Info",  # renamed from reactionstop
}

# SUDO categories (ordered)
_SUDO_CATEGORY_TITLES: List[str] = [
    "🛡️ Moderation & Cleanup",
    "🏷️ Reactions & Buttons",
    "✉️ Direct Messages & Editing",
    "📰 Embeds & Refreshers",
    "👥 Roles & Members",
    "🗃️ Backup & Admin",
    "🧮 Counters & Reports",
    "🧰 Utilities",
    "📦 Misc",
]

# Map base sudo command -> category title
_SUDO_CATEGORY_MAP: Dict[str, str] = {
    # Moderation & Cleanup
    "sudo_purge": "🛡️ Moderation & Cleanup",
    "sudo_remove_reaction": "🛡️ Moderation & Cleanup",
    "sudo_delete_category_channels": "🛡️ Moderation & Cleanup",
    "sudo_check_dangerous_perms": "🛡️ Moderation & Cleanup",

    # Reactions & Buttons
    "sudo_remove_buttons": "🏷️ Reactions & Buttons",
    "sudo_add_reaction": "🏷️ Reactions & Buttons",

    # Direct Messages & Editing
    "sudo_send_message": "✉️ Direct Messages & Editing",
    "sudo_edit_message": "✉️ Direct Messages & Editing",
    "sudo_edit_dm": "✉️ Direct Messages & Editing",  # moved from public edit_dm -> sudo_edit_dm
    "sudo_edit_embed": "✉️ Direct Messages & Editing",

    # Embeds & Refreshers
    "sudo_refresh_channels": "📰 Embeds & Refreshers",
    "sudo_refresh_embeds": "📰 Embeds & Refreshers",
    "sudo_refresh_quick_guide": "📰 Embeds & Refreshers",

    # Roles & Members
    "sudo_roles_members": "👥 Roles & Members",
    "sudo_roles_reset": "👥 Roles & Members",
    "sudo_add_role_everyone": "👥 Roles & Members",
    "sudo_remove_role_everyone": "👥 Roles & Members",

    # Backup & Admin
    "sudo_backup_messages": "🗃️ Backup & Admin",
    "sudo_backup_category": "🗃️ Backup & Admin",
    "sudo_create_event": "🗃️ Backup & Admin",
    "sudo_rename_channel": "🗃️ Backup & Admin",

    # Counters & Reports
    "sudo_count_messages": "🧮 Counters & Reports",
    "sudo_count_mentions": "🧮 Counters & Reports",
    "sudo_list_perms": "🧮 Counters & Reports",
    "sudo_pc_status": "🧮 Counters & Reports",
    "sudo_send_coins": "🧮 Counters & Reports",

    # Utilities
    "sudo_commands": "🧰 Utilities",
}

def _category_for_command(name: str, is_sudo: bool) -> str:
    base = name.lower().strip()
    if is_sudo:
        return _SUDO_CATEGORY_MAP.get(base, "📦 Misc")
    if base in _PUBLIC_CATEGORY_MAP:
        return _PUBLIC_CATEGORY_MAP[base]
    # Fallback heuristics for unmapped names
    if base in {"l", "s", "b", "p", "sp", "r", "ch", "chs", "chan"}:
        return "🛠️ Utilities"
    return "📦 Misc"

def _categorize(
    cmds: Iterable[commands.Command],
    prefix: str,
    *,
    is_sudo: bool,
) -> List[Tuple[str, str]]:
    """
    Return a list of (category_title, joined_items) fields in desired order,
    chunked to fit Discord field limits.
    """
    bucket: Dict[str, List[str]] = {}
    for c in cmds:
        name = (c.qualified_name or "").lower()
        cat = _category_for_command(name, is_sudo=is_sudo)
        bucket.setdefault(cat, []).append(_fmt_cmd_name(c, prefix))

    for v in bucket.values():
        v.sort(key=lambda s: s.lower())

    fields: List[Tuple[str, str]] = []
    order = _SUDO_CATEGORY_TITLES if is_sudo else _PUBLIC_CATEGORY_TITLES
    for cat in order:
        names = bucket.get(cat, [])
        if not names:
            continue
        for i, chunk in enumerate(_chunk_text(names, " • ", MAX_FIELD_VALUE), start=1):
            fname = cat if i == 1 else f"{cat} (cont.)"
            fields.append((fname, chunk))
    return fields

# ---------- public / sudo builders ----------
def build_public_commands_embeds(bot: commands.Bot, prefix: str) -> List[discord.Embed]:
    public_cmds = [c for c in bot.commands if _is_public_command(c)]
    fields = _categorize(public_cmds, prefix, is_sudo=False)
    return _build_embeds_from_fields(
        title="🎉💰 Server Commands 💰🎉",
        description="",
        fields=fields,
        color=discord.Color.blurple(),
    )

def build_sudo_commands_embeds(
    bot: commands.Bot,
    prefix: str,
    *,
    show_admin_warning: bool,
) -> List[discord.Embed]:
    sudo_cmds = [c for c in bot.commands if _is_sudo_like(c)]
    fields = _categorize(sudo_cmds, prefix, is_sudo=True)
    footer = "Elevated permissions required." if show_admin_warning else None
    return _build_embeds_from_fields(
        title="🔐 Sudo Commands",
        description="",
        fields=fields,
        footer=footer,
        color=discord.Color.red(),
    )

# (Optional) still available if you want to append slash commands to the *last* embed
def add_slash_commands_section(embed: discord.Embed, bot: commands.Bot):
    try:
        app_cmds = bot.tree.get_commands()
        if not app_cmds:
            return
        names = [f"`/{c.name}`" for c in app_cmds if getattr(c, "name", None)]
        if not names:
            return
        for i, chunk in enumerate(_chunk_text(names, " • ", MAX_FIELD_VALUE), start=1):
            fname = "🧭 Slash Commands" if i == 1 else "🧭 Slash Commands (cont.)"
            embed.add_field(name=fname, value=chunk, inline=False)
    except Exception:
        pass
