# cogs/invites_handler/cog.py
from __future__ import annotations

import asyncio
import logging
import discord
from discord.ext import commands

from configs.config_general import AUTHORIZED_USER_ID
from configs.config_channels import CHITTY_CHAT_CHANNEL_ID

from cogs.onboarding.invites_handler.data import (
    invite_code_data,
    invite_message_data,
    load_invite_codes,
    load_invite_data,
    load_invite_rewards,
    save_invite_codes,
    save_invite_data,
)
from cogs.onboarding.invites_handler.display import format_invite_leaderboard
from cogs.onboarding.invites_handler.logic import handle_invite_reward, VANITY_ID
from cogs.onboarding.invites_handler.track_init import initialize_invites_cache

log = logging.getLogger(__name__)


class InvitesHandler(commands.Cog):
    """
    Tracks which invite brought a member, rewards inviters,
    updates counts on leave, and provides !invites command.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # --------------------------
    # lifecycle
    # --------------------------
    @commands.Cog.listener("on_ready")
    async def _on_ready_once(self):
        if getattr(self.bot, "_invites_handler_ready", False):
            return
        self.bot._invites_handler_ready = True

        # load persisted stores
        load_invite_data()
        load_invite_codes()
        load_invite_rewards()

        # build initial cache
        await initialize_invites_cache(self.bot)
        log.info("[Invites] Initialized")

    # --------------------------
    # member join / leave
    # --------------------------
    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return
        log.info(f"[Join] {member} ({member.id})")

        await self._track_invites(member)
        await self._react_to_recent_message(member)

    @commands.Cog.listener("on_member_remove")
    async def on_member_remove(self, member: discord.Member):
        if getattr(member, "bot", False):
            return

        uid = str(member.id)
        log.info(f"[Leave] {member} ({uid})")

        for inviter_id, entry in invite_message_data.items():
            users = entry.get("invited_users", [])
            if uid in users:
                users.remove(uid)
                entry["count"] = max(0, int(entry.get("count", 0)) - 1)
                save_invite_data()
                log.info(f"[Leave] Decremented {inviter_id}; now {entry['count']}")
                break
        else:
            log.warning(f"[Leave] No inviter record for {uid}")

    # --------------------------
    # command: !invites [@user]
    # --------------------------
    @commands.command(name="invites", help="Show invite leaderboard or (admin) a user's invitees.")
    @commands.guild_only()
    async def invites_cmd(self, ctx: commands.Context, arg: str | None = None):
        log.info(f"[Command] !invites by {ctx.author} — arg={arg}")

        # Admin check for checking specific user's invited list via mention
        if ctx.message.mentions:
            if ctx.author.id != AUTHORIZED_USER_ID:
                await ctx.send("⛔ You're not authorized to check others' invites.")
                return

            member = ctx.message.mentions[0]
            inviter_id = str(member.id)
            entry = invite_message_data.get(inviter_id, {"count": 0, "invited_users": []})

            if entry["invited_users"]:
                mentions = [f"<@{uid}>" for uid in entry["invited_users"]]
                await ctx.send(
                    f"📨 **{member.display_name}** has invited **{entry['count']}** member(s):\n" +
                    ", ".join(mentions)
                )
            else:
                await ctx.send(f"📨 **{member.display_name}** has invited **{entry['count']}** member(s) so far.")
            return

        if not invite_message_data:
            await ctx.send("📭 No invites tracked yet.")
            return

        sorted_invites = sorted(
            invite_message_data.items(),
            key=lambda x: x[1].get("count", 0),
            reverse=True,
        )
        embed = format_invite_leaderboard(sorted_invites, ctx.guild)
        await ctx.send(embed=embed)

    # --------------------------
    # internals
    # --------------------------
    async def _track_invites(self, member: discord.Member):
        """Detect which invite was used and update counts/messages."""
        guild = member.guild
        try:
            before = getattr(self.bot, "invites_cache", {}).get(guild.id, [])
            after = await guild.invites()
            self.bot.invites_cache[guild.id] = after

            # find invite with incremented uses
            used = None
            for new in after:
                old = next((o for o in before if o.code == new.code), None)
                if old and new.uses > old.uses:
                    used = new
                    break

            if used:
                inviter = used.inviter or member.guild.me  # fallback just in case
                invite_code_data[used.code] = {
                    "inviter_id": str(getattr(inviter, "id", "vanity")),
                    "uses": used.uses,
                }
                await handle_invite_reward(guild, inviter, member)
                save_invite_codes()
                log.info(f"[Join] Invite {used.code} by {inviter} recorded.")
                return

            # fallback: compare to stored data
            for inv in after:
                data = invite_code_data.get(inv.code)
                if data and inv.uses > data.get("uses", 0):
                    inviter_id = int(data["inviter_id"])
                    inviter = guild.get_member(inviter_id) or await self.bot.fetch_user(inviter_id)
                    invite_code_data[inv.code]["uses"] = inv.uses
                    await handle_invite_reward(guild, inviter, member)
                    save_invite_codes()
                    log.info(f"[Join-Fallback] Invite {inv.code} by {inviter} recorded.")
                    return

            # vanity URL case
            log.warning(f"[Join] No invite delta found for {member}; treating as vanity.")
            entry = invite_message_data.get(VANITY_ID, {"count": 0, "msg_id": None, "invited_users": []})
            mid = str(member.id)
            if mid not in entry["invited_users"]:
                entry["invited_users"].append(mid)
                entry["count"] = int(entry.get("count", 0)) + 1
                invite_message_data[VANITY_ID] = entry
                save_invite_data()

        except Exception as e:
            log.error(f"[Join] Invite tracking failed: {e}", exc_info=True)

    async def _react_to_recent_message(self, member: discord.Member):
        """Look for the member's last message in chitty-chat and wave 👋🏼 to it."""
        await asyncio.sleep(1)  # give time for any immediate messages
        try:
            channel = member.guild.get_channel(CHITTY_CHAT_CHANNEL_ID)
            if not channel:
                log.warning("[Join] Chitty-chat channel not found.")
                return

            async for msg in channel.history(limit=5):
                if msg.author.id == member.id:
                    try:
                        await msg.add_reaction("👋🏼")
                        log.info(f"[Join] Reacted to {member}'s message.")
                    except Exception:
                        pass
                    return

            log.info(f"[Join] No recent message by {member} in chitty-chat.")
        except Exception as e:
            log.error(f"[Join] Failed reaction step: {e}", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(InvitesHandler(bot))
