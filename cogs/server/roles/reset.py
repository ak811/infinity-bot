from __future__ import annotations
import asyncio
from typing import List, Optional
import discord
from configs.config_roles import ALMIGHTY_ROLE_ID, LOOT_AND_LEGENDS_ROLES, MEMBER_ROLE_ID
from .formatting import send_embed

def _authorized(ctx) -> bool:
    return bool(ctx.author.guild_permissions.administrator or any(r.id == ALMIGHTY_ROLE_ID for r in getattr(ctx.author, "roles", [])))

async def reset_level_roles(ctx):
    guild: discord.Guild = ctx.guild

    if not _authorized(ctx):
        e = discord.Embed(title="⛔ Permission denied", description="Requires **Administrator** or **Almighty** role.", color=discord.Color.red())
        await send_embed(ctx, e); return

    if not guild.me.guild_permissions.manage_roles:
        e = discord.Embed(title="⚠️ Missing permission", description="I need **Manage Roles**.", color=discord.Color.orange())
        await send_embed(ctx, e); return

    level_ids = [rid for (rid, *_rest) in LOOT_AND_LEGENDS_ROLES]
    level_roles: List[discord.Role] = [guild.get_role(rid) for rid in level_ids if guild.get_role(rid)]
    member_role: Optional[discord.Role] = guild.get_role(MEMBER_ROLE_ID)

    # Hierarchy checks
    uneditable = [r for r in level_roles if r and r >= guild.me.top_role]
    if uneditable or (member_role and member_role >= guild.me.top_role):
        lines = [f"• {r.name} ({r.id})" for r in uneditable if r]
        if member_role and member_role >= guild.me.top_role: lines.append(f"• {member_role.name} ({member_role.id})")
        e = discord.Embed(title="⚠️ Role hierarchy issue", description="My top role is not high enough:\n" + "\n".join(lines), color=discord.Color.orange())
        await send_embed(ctx, e); return

    affected = removed = added = 0
    await send_embed(ctx, discord.Embed(title="🔧 Resetting level roles…", color=discord.Color.blurple()))

    for i, member in enumerate(guild.members):
        if member.bot: continue
        to_remove = [r for r in level_roles if r and r in member.roles]
        changed = False
        if to_remove:
            try: await member.remove_roles(*to_remove, reason="!roles_reset"); removed += len(to_remove); changed = True
            except discord.Forbidden: pass
        if member_role and member_role not in member.roles:
            try: await member.add_roles(member_role, reason="!roles_reset"); added += 1; changed = True
            except discord.Forbidden: pass
        if changed: affected += 1
        if i % 10 == 0: await asyncio.sleep(0.3)

    desc = f"**Affected members:** {affected}\n**Level roles removed:** {removed}\n**Member role added:** {added}\n"
    await send_embed(ctx, discord.Embed(title="✅ Reset complete", description=desc, color=discord.Color.green()))
