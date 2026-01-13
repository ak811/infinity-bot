# cogs/server/channels/archive_cog.py
from __future__ import annotations
import discord
from discord.ext import commands, tasks
from . import activity, mover, positions
from .archive_config import SWEEP_UTC_TIME, REQUIRE_PUBLIC, INACTIVITY_DAYS, ARCHIVE_CATEGORY_NAME

def _is_public(ch: discord.abc.GuildChannel) -> bool:
    try: return ch.permissions_for(ch.guild.default_role).view_channel
    except Exception: return False

class ArchiveCog(commands.Cog):
    """Archives inactive PUBLIC channels and restores on activity."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ready_boot = False
        self.daily_sweep.change_interval(time=SWEEP_UTC_TIME)

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ready_boot: return
        await activity.bootstrap(self.bot)
        self.daily_sweep.start()
        self._ready_boot = True

    @tasks.loop(time=SWEEP_UTC_TIME)
    async def daily_sweep(self):
        for g in self.bot.guilds:
            cat = await mover.get_archive_category(g)
            if not cat: continue
            for ch in list(g.text_channels) + list(g.voice_channels):
                await mover.archive_if_inactive(g, ch)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Count messages from both TextChannels AND VoiceChannels (voice text chat)
        if message.guild is None:
            return
        ch = message.channel
        if not isinstance(ch, (discord.TextChannel, discord.VoiceChannel)):
            return

        # Record activity (this function already self-checks public visibility)
        await activity.update_from_message(message)

        # 🔑 Always attempt unarchive on any message, even if not public
        await mover.unarchive_on_message(message)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        await activity.update_from_voice_state(member, before, after)

    # ---- Admin commands (sudo_*) ----
    @commands.command(name="sudo_is_channel_active", aliases=["sudo_is_channel_active?"])
    @commands.has_permissions(administrator=True)
    async def sudo_is_channel_active(self, ctx: commands.Context, channel: discord.abc.GuildChannel | None = None):
        ch = channel or ctx.channel
        public = _is_public(ch)
        active = await activity.is_channel_active(ch) if public else True
        kind = "text" if isinstance(ch, discord.TextChannel) else "voice" if isinstance(ch, discord.VoiceChannel) else "other"
        msg = (f"Channel: {ch.mention}\nType: **{kind}**\nPublic: **{'Yes' if public else 'No'}**\n"
               f"Inactive window: **{INACTIVITY_DAYS} days**\nActive now: **{'✅ Yes' if active else '❌ No'}**")
        await ctx.reply(msg)

    @commands.command(name="sudo_archive_ensure", aliases=["sudo_archive_create"])
    @commands.has_permissions(administrator=True, manage_channels=True)
    async def sudo_archive_ensure(self, ctx: commands.Context):
        """Create a public ArchiveCategory if missing."""
        g = ctx.guild
        if not g: return
        cat = await mover.get_archive_category(g)
        if cat:
            return await ctx.reply(f"Archive category already exists: **{cat.name}**")
        overwrites = {g.default_role: discord.PermissionOverwrite(view_channel=True)}
        try:
            new_cat = await g.create_category_channel(ARCHIVE_CATEGORY_NAME, overwrites=overwrites)
            await ctx.reply(f"Created archive category: **{new_cat.name}** (public).")
        except discord.Forbidden:
            await ctx.reply("I lack permissions to create categories.")
        except Exception as e:
            await ctx.reply(f"Failed to create archive category: `{e}`")

    @commands.command(name="sudo_archive_sweep", aliases=["sudo_archive_inactive", "sudo_archive_now"])
    @commands.has_permissions(administrator=True)
    async def sudo_archive_sweep(self, ctx: commands.Context):
        """Archive all inactive PUBLIC channels right now."""
        g = ctx.guild
        if not g:
            return await ctx.reply("This command can only be used in a server.")
        cat = await mover.get_archive_category(g)
        if not cat:
            return await ctx.reply("Archive category not found. Run **!sudo_archive_ensure** first.")

        count = 0
        for ch in list(g.text_channels) + list(g.voice_channels):
            try:
                if await mover.archive_if_inactive(g, ch):
                    count += 1
            except Exception:
                pass  # continue on errors

        await ctx.reply(f"Archived **{count}** inactive public channel(s).")

    @commands.command(name="sudo_unarchive_sweep", aliases=["sudo_unarchive_all"])
    @commands.has_permissions(administrator=True)
    async def sudo_unarchive_sweep(self, ctx: commands.Context):
        """Restore ALL channels from the Archive category back to their saved original spots (public or private)."""
        g = ctx.guild
        if not g:
            return await ctx.reply("This command can only be used in a server.")
        cat = await mover.get_archive_category(g)
        if not cat:
            return await ctx.reply("Archive category not found.")

        to_restore = list(cat.text_channels) + list(cat.voice_channels)
        if not to_restore:
            return await ctx.reply("No channels to restore in the archive category.")

        restored = 0
        for ch in to_restore:
            try:
                # No public-visibility check here — restore everything in Archive
                await positions.restore_to_original(g, ch)
                restored += 1
            except Exception:
                # keep going on errors
                pass

        await ctx.reply(f"Restored **{restored}** channel(s) from the archive.")
        
async def setup(bot: commands.Bot):
    await bot.add_cog(ArchiveCog(bot))
