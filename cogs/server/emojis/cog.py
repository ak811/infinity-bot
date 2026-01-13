# cogs/server/emojis/cog.py
from __future__ import annotations
import discord
from discord.ext import commands
from discord import app_commands
from discord.app_commands import checks as ac_checks
from io import BytesIO
import random

from . import checks, errors, events
from .commands_emojis import build_emojis_pages_text
from .commands_stickers import build_stickers_list
from .commands_inspect import build_emoji_detail, build_sticker_detail, build_emoji_search
from .constants import COLOR_ERROR, COLOR_LISTS
from .pagination import PaginatorView, PaginatorTextView, message_kwargs_for_page

# Role/rank helpers
from cogs.server.roles.rank import get_highest_loot_legends_role_index
from configs.config_roles import LOOT_AND_LEGENDS_ROLES
# Per-guild scoping for instant availability
from configs.config_general import BOT_GUILD_ID


def _parse_page_arg(arg: str | None) -> int | None:
    if not arg:
        return None
    lower = arg.strip().lower()
    for prefix in ("page", "p"):
        if lower.startswith(prefix):
            rest = lower[len(prefix):].strip(" :#")
            try:
                n = int(rest)
                return n if n >= 1 else None
            except ValueError:
                return None
    try:
        n = int(lower)
        return n if n >= 1 else None
    except ValueError:
        return None

def _help_embed(title: str, lines: list[str]) -> discord.Embed:
    """
    Build a simple help/usage embed using the list color.
    """
    return discord.Embed(
        title=title,
        description="\n".join(lines),
        color=COLOR_LISTS
    )

# ------- Role/perm gate utilities ---------------------------------------------

def _legend_index() -> int:
    LEGEND_ROLE_ID = 1330679104705527818  # update if your Legend role ID changes
    for i, (rid, *_rest) in enumerate(LOOT_AND_LEGENDS_ROLES):
        if rid == LEGEND_ROLE_ID:
            return i
    return max(0, len(LOOT_AND_LEGENDS_ROLES) - 2)

def _is_legend_or_above(member: discord.Member) -> bool:
    return get_highest_loot_legends_role_index(member) >= _legend_index()

def _is_admin(member: discord.Member) -> bool:
    return bool(member.guild_permissions.administrator)

def _manage_perm_ok(guild: discord.Guild) -> bool:
    me = guild.me
    return bool(me and me.guild_permissions.manage_emojis_and_stickers)


class EmojisCog(commands.Cog):
    """List and inspect server emojis & stickers, plus manage via slash commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ==================== Prefix Commands (grouped) ====================

    # ---- EMOJIS group -------------------------------------------------

    @commands.group(name="emojis", invoke_without_command=True)
    @checks.rate_limited_guild()
    async def emojis_group(self, ctx: commands.Context, *, arg: str | None = None):
        """
        !emojis → shows usage
        !emojis list [page N] → jumbo list (existing behavior)
        !emojis search <query> → find by name
        !emojis slots → used/left (Static vs Animated)
        !emojis random → random (unlocked preferred)
        """
        if ctx.invoked_subcommand is not None:
            return
        help_lines = [
            "• `!emojis list` — show server emojis (jumbo, paginated).",
            "  • Jump to a page: `!emojis list page 2` or `!emojis list 2`",
            "• `!emojis search <query>` — paginated search by name.",
            "• `!emojis slots` — used/left for **Static** and **Animated**.",
            "• `!emojis random` — shows a random emoji (prefers unlocked).",
            "• `!emoji info <name|id>` — details card for a specific emoji.",
        ]
        await ctx.send(embed=_help_embed("😀 Emoji commands", help_lines))

    @emojis_group.command(name="list")
    @checks.rate_limited_guild()
    async def emojis_list(self, ctx: commands.Context, *, arg: str | None = None):
        try:
            guild = checks.require_guild(ctx); checks.ensure_intents(self.bot)
            pages = build_emojis_pages_text(guild, per_line=5, lines_per_page=5)
            page_arg = _parse_page_arg(arg)
            idx = (page_arg - 1) if page_arg else 0
            idx = max(0, min(idx, len(pages) - 1))
            view = PaginatorTextView(pages, start=idx, author_id=ctx.author.id) if len(pages) > 1 else None
            await ctx.send(content=pages[idx], view=view)
        except Exception as exc:
            await ctx.send(embed=self._err(errors.user_message(exc)))

    @emojis_group.command(name="search")
    @checks.rate_limited_guild()
    async def emojis_search(self, ctx: commands.Context, *, query: str):
        try:
            guild = checks.require_guild(ctx); checks.ensure_intents(self.bot)
            pages = build_emoji_search(guild, query)
            view = PaginatorView(pages, author_id=ctx.author.id) if len(pages) > 1 else None
            await ctx.send(embed=pages[0], view=view)
        except Exception as exc:
            await ctx.send(embed=self._err(errors.user_message(exc)))

    @emojis_group.command(name="slots")
    @checks.rate_limited_guild()
    async def emojis_slots(self, ctx: commands.Context):
        """
        Report static vs animated usage separately.
        Discord exposes `guild.emoji_limit` as the per-type cap (static and animated each have this cap).
        """
        try:
            guild = checks.require_guild(ctx); checks.ensure_intents(self.bot)

            total_limit = getattr(guild, "emoji_limit", 50)  # defensive default
            static_used = sum(1 for e in guild.emojis if not e.animated)
            anim_used = sum(1 for e in guild.emojis if getattr(e, "animated", False))

            static_left = max(0, total_limit - static_used)
            anim_left = max(0, total_limit - anim_used)

            em = discord.Embed(title="😀 Emoji Slots", color=discord.Color.blurple())
            em.add_field(
                name="Static",
                value=f"**{static_used} / {total_limit}** used\n**{static_left}** left",
                inline=True,
            )
            em.add_field(
                name="Animated",
                value=f"**{anim_used} / {total_limit}** used\n**{anim_left}** left",
                inline=True,
            )
            await ctx.send(embed=em)

        except Exception as exc:
            await ctx.send(embed=self._err(errors.user_message(exc)))

    @emojis_group.command(name="random")
    @checks.rate_limited_guild()
    async def emojis_random(self, ctx: commands.Context):
        """
        Send a random emoji token. Prefer unlocked (no role restrictions); if none, fallback to any.
        Content-only so Discord renders it jumbo.
        """
        try:
            guild = checks.require_guild(ctx); checks.ensure_intents(self.bot)
            if not guild.emojis:
                return await ctx.send(embed=self._err("No emojis found."))

            unlocked = [e for e in guild.emojis if not getattr(e, "roles", None)]
            pool = unlocked or list(guild.emojis)
            e = random.choice(pool)
            token = f"<{'a' if getattr(e, 'animated', False) else ''}:{e.name}:{e.id}>"
            await ctx.send(content=token)
        except Exception as exc:
            await ctx.send(embed=self._err(errors.user_message(exc)))

    # ---- EMOJI single-command group (info) -----------------------------------

    @commands.group(name="emoji", invoke_without_command=True)
    @checks.rate_limited_guild()
    async def emoji_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is not None:
            return
        await ctx.send("Usage: `!emoji info <name|id>`")

    @emoji_group.command(name="info")
    @checks.rate_limited_guild()
    async def emoji_info(self, ctx: commands.Context, *, token: str):
        try:
            guild = checks.require_guild(ctx); checks.ensure_intents(self.bot)
            em = build_emoji_detail(guild, token)
            if not em: raise errors.ItemNotFoundError()
            await ctx.send(embed=em)
        except Exception as exc:
            await ctx.send(embed=self._err(errors.user_message(exc)))

    # ---- STICKERS group ------------------------------------------------

    @commands.group(name="stickers", invoke_without_command=True)
    @checks.rate_limited_guild()
    async def stickers_group(self, ctx: commands.Context, *, arg: str | None = None):
        """
        !stickers → shows usage
        !stickers list [page N] → one sticker per page (image)
        !stickers slots → pool usage
        !stickers random → random sticker
        """
        if ctx.invoked_subcommand is not None:
            return
        help_lines = [
            "• `!stickers list` — show server stickers (one per page, with image).",
            "  • Jump to a page: `!stickers list page 2` or `!stickers list 2`",
            "• `!stickers slots` — used/left sticker slots (shared pool).",
            "• `!stickers random` — shows a random sticker.",
            "• `!sticker info <name|id>` — details card for a specific sticker.",
        ]
        await ctx.send(embed=_help_embed("🏷️ Sticker commands", help_lines))

    @stickers_group.command(name="list")
    @checks.rate_limited_guild()
    async def stickers_list(self, ctx: commands.Context, *, arg: str | None = None):
        try:
            guild = checks.require_guild(ctx); checks.ensure_intents(self.bot)
            pages = build_stickers_list(guild)
            page_arg = _parse_page_arg(arg)
            idx = (page_arg - 1) if page_arg else 0
            idx = max(0, min(idx, len(pages) - 1))
            view = PaginatorView(pages, start=idx, author_id=ctx.author.id) if len(pages) > 1 else None
            kwargs = message_kwargs_for_page(pages[idx])
            if view:
                kwargs["view"] = view
            await ctx.send(**kwargs)
        except Exception as exc:
            await ctx.send(embed=self._err(errors.user_message(exc)))

    @stickers_group.command(name="slots")
    @checks.rate_limited_guild()
    async def stickers_slots(self, ctx: commands.Context):
        """
        Sticker pool has a single limit (Guild.sticker_limit). We also show a friendly breakdown
        of how many are Lottie vs PNG/APNG, but the pool is shared.
        """
        try:
            guild = checks.require_guild(ctx); checks.ensure_intents(self.bot)

            total_limit = getattr(guild, "sticker_limit", 15)  # defensive default
            total_used = len(guild.stickers)

            # Breakdown (informational)
            lottie_used = 0
            raster_used = 0
            for s in guild.stickers:
                fmt = getattr(s, "format", getattr(s, "format_type", None))
                if str(fmt).endswith("lottie"):
                    lottie_used += 1
                else:
                    raster_used += 1

            left = max(0, total_limit - total_used)

            em = discord.Embed(title="🏷️ Sticker Slots", color=discord.Color.green())
            em.add_field(
                name="Total",
                value=f"**{total_used} / {total_limit}** used\n**{left}** left",
                inline=False,
            )
            em.add_field(name="Breakdown", value=f"Lottie: **{lottie_used}**\nPNG/APNG: **{raster_used}**", inline=True)
            await ctx.send(embed=em)

        except Exception as exc:
            await ctx.send(embed=self._err(errors.user_message(exc)))

    @stickers_group.command(name="random")
    @checks.rate_limited_guild()
    async def stickers_random(self, ctx: commands.Context):
        """
        Send a random sticker as a detail card (with image if available).
        """
        try:
            guild = checks.require_guild(ctx); checks.ensure_intents(self.bot)
            if not guild.stickers:
                return await ctx.send(embed=self._err("No stickers found."))
            s = random.choice(list(guild.stickers))
            em = build_sticker_detail(s)
            if not em:
                return await ctx.send(embed=self._err("Could not render sticker."))
            await ctx.send(embed=em)
        except Exception as exc:
            await ctx.send(embed=self._err(errors.user_message(exc)))

    # ---- STICKER single-command group (info) ----------------------------

    @commands.group(name="sticker", invoke_without_command=True)
    @checks.rate_limited_guild()
    async def sticker_group(self, ctx: commands.Context):
        if ctx.invoked_subcommand is not None:
            return
        await ctx.send("Usage: `!sticker info <name|id>`")

    @sticker_group.command(name="info")
    @checks.rate_limited_guild()
    async def sticker_info(self, ctx: commands.Context, *, token: str):
        try:
            guild = checks.require_guild(ctx); checks.ensure_intents(self.bot)
            em = build_sticker_detail(guild, token)
            if not em: raise errors.ItemNotFoundError()
            await ctx.send(embed=em)
        except Exception as exc:
            await ctx.send(embed=self._err(errors.user_message(exc)))

    # ==================== Events passthrough (unchanged) ====================

    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        events.on_emojis_update(guild)

    @commands.Cog.listener()
    async def on_guild_stickers_update(self, guild, before, after):
        events.on_stickers_update(guild)

    # ==================== Error helper (unchanged) ====================

    def _err(self, msg: str) -> discord.Embed:
        return discord.Embed(title="Error", description=msg, color=COLOR_ERROR)

    # ==================== Slash Commands (existing) ====================
    # These remain intact; included for completeness.

    # ---- /emoji_add (Legend+) -------------------------------------------

    @app_commands.command(name="emoji_add", description="Add a custom emoji to this server.")
    @app_commands.describe(
        name="Name for the emoji (letters, numbers, underscores).",
        image="PNG/JPG for static, GIF for animated. ≤ 256 KB."
    )
    @app_commands.guild_only()
    @app_commands.guilds(discord.Object(id=BOT_GUILD_ID))
    async def emoji_add(self, interaction: discord.Interaction, name: str, image: discord.Attachment):
        try:
            await self.interaction_legend_gate(interaction)
            await interaction.response.defer(ephemeral=False)

            if not image.content_type or not any(
                t in image.content_type for t in ("image/png", "image/jpeg", "image/gif", "image/apng")
            ):
                return await interaction.followup.send(
                    "Please upload a valid image (PNG/JPG/GIF/APNG).", ephemeral=False
                )

            data = await image.read()
            if len(data) > 256 * 1024:
                return await interaction.followup.send(
                    "Emoji image must be **≤ 256 KB**.", ephemeral=False
                )

            emoji = await interaction.guild.create_custom_emoji(
                name=name,
                image=data,
                reason=f"/emoji_add by {interaction.user} ({interaction.user.id})"
            )

            events.on_emojis_update(interaction.guild)
            token = f"<{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>"
            await interaction.followup.send(f"Created {token}", ephemeral=False)

        except app_commands.CheckFailure as e:
            if interaction.response.is_done():
                await interaction.followup.send(str(e), ephemeral=False)
            else:
                await interaction.response.send_message(str(e), ephemeral=False)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to create emojis here.", ephemeral=False)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Discord error while creating emoji: {e}", ephemeral=False)

    # ---- /emoji_remove (Admins only) ------------------------------------

    @app_commands.command(name="emoji_remove", description="Remove a custom emoji by name or ID.")
    @app_commands.describe(token="Emoji name or ID (e.g. 'partyparrot' or '123456789012345678').")
    @app_commands.guild_only()
    @app_commands.guilds(discord.Object(id=BOT_GUILD_ID))
    @ac_checks.has_permissions(administrator=True)  # UI visibility + extra safety
    @app_commands.default_permissions(administrator=True)
    async def emoji_remove(self, interaction: discord.Interaction, token: str):
        from .resolve import emoji as resolve_emoji  # local import to avoid cycles
        try:
            await self.interaction_admin_gate(interaction)
            await interaction.response.defer(ephemeral=False)

            e = resolve_emoji(interaction.guild, token)
            if not e:
                return await interaction.followup.send("I couldn’t find a matching emoji.", ephemeral=False)

            await e.delete(reason=f"/emoji_remove by {interaction.user} ({interaction.user.id})")
            events.on_emojis_update(interaction.guild)
            await interaction.followup.send(f"Deleted `:{e.name}:` ({e.id}).", ephemeral=False)

        except app_commands.CheckFailure as e:
            if interaction.response.is_done():
                await interaction.followup.send(str(e), ephemeral=False)
            else:
                await interaction.response.send_message(str(e), ephemeral=False)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to delete emojis here.", ephemeral=False)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Discord error while deleting emoji: {e}", ephemeral=False)

    # ---- /sticker_add (Legend+) -----------------------------------------

    @app_commands.command(name="sticker_add", description="Add a sticker to this server (PNG/APNG/Lottie).")
    @app_commands.describe(
        name="Name of the sticker.",
        file="PNG/APNG (≤ 512 KB) or Lottie JSON (≤ 500 KB).",
        emoji="Related Unicode emoji tag (required by Discord).",
        description="Optional description for the sticker."
    )
    @app_commands.guild_only()
    @app_commands.guilds(discord.Object(id=BOT_GUILD_ID))
    async def sticker_add(
        self,
        interaction: discord.Interaction,
        name: str,
        file: discord.Attachment,
        emoji: str,
        description: str | None = None,
    ):
        try:
            await self.interaction_legend_gate(interaction)
            await interaction.response.defer(ephemeral=False)

            if not file.content_type:
                return await interaction.followup.send("Please upload PNG/APNG or Lottie JSON.", ephemeral=False)

            is_lottie = "json" in file.content_type
            is_image = any(t in file.content_type for t in ("image/png", "image/apng"))

            if not (is_lottie or is_image):
                return await interaction.followup.send(
                    "Unsupported file type. Use PNG/APNG or Lottie JSON.", ephemeral=False
                )

            b = await file.read()
            if len(b) > 512 * 1024:
                return await interaction.followup.send(
                    "Sticker file seems too large (max ~512 KB).", ephemeral=False
                )

            fp = BytesIO(b)
            upfile = discord.File(fp, filename=file.filename or ("sticker.json" if is_lottie else "sticker.png"))

            sticker = await interaction.guild.create_sticker(
                name=name,
                description=(description or ""),
                emoji=emoji,
                file=upfile,
                reason=f"/sticker_add by {interaction.user} ({interaction.user.id})"
            )

            events.on_stickers_update(interaction.guild)
            await interaction.followup.send(f"Created sticker `:{sticker.name}:` ({sticker.id}).", ephemeral=False)

        except app_commands.CheckFailure as e:
            if interaction.response.is_done():
                await interaction.followup.send(str(e), ephemeral=False)
            else:
                await interaction.response.send_message(str(e), ephemeral=False)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to create stickers here.", ephemeral=False)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Discord error while creating sticker: {e}", ephemeral=False)

    # ---- /sticker_remove (Admins only) ----------------------------------

    @app_commands.command(name="sticker_remove", description="Remove a sticker by name or ID.")
    @app_commands.describe(token="Sticker name or ID.")
    @app_commands.guild_only()
    @app_commands.guilds(discord.Object(id=BOT_GUILD_ID))
    @ac_checks.has_permissions(administrator=True)  # UI visibility + extra safety
    @app_commands.default_permissions(administrator=True)
    async def sticker_remove(self, interaction: discord.Interaction, token: str):
        from .resolve import sticker as resolve_sticker
        try:
            await self.interaction_admin_gate(interaction)
            await interaction.response.defer(ephemeral=False)

            s = resolve_sticker(interaction.guild, token)
            if not s:
                return await interaction.followup.send("I couldn’t find a matching sticker.", ephemeral=False)

            await s.delete(reason=f"/sticker_remove by {interaction.user} ({interaction.user.id})")
            events.on_stickers_update(interaction.guild)
            await interaction.followup.send(f"Deleted sticker `:{s.name}:` ({s.id}).", ephemeral=False)

        except app_commands.CheckFailure as e:
            if interaction.response.is_done():
                await interaction.followup.send(str(e), ephemeral=False)
            else:
                await interaction.response.send_message(str(e), ephemeral=False)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to delete stickers here.", ephemeral=False)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Discord error while deleting sticker: {e}", ephemeral=False)

    # ==================== Common gates for slash commands ====================

    async def interaction_legend_gate(self, interaction: discord.Interaction) -> None:
        """
        Gate for 'add' commands: Must be in guild, user Legend-or-above, bot has Manage Emojis & Stickers.
        """
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise app_commands.CheckFailure("This command can only be used in a server.")
        # if not _is_legend_or_above(interaction.user):
        #     raise app_commands.CheckFailure("You must be **Legend** or higher to use this.")
        if not _manage_perm_ok(interaction.guild):
            raise app_commands.CheckFailure("I’m missing the **Manage Emojis and Stickers** permission.")

    async def interaction_admin_gate(self, interaction: discord.Interaction) -> None:
        """
        Gate for 'remove' commands: Must be in guild, user Administrator, bot has Manage Emojis & Stickers.
        """
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            raise app_commands.CheckFailure("This command can only be used in a server.")
        if not _is_admin(interaction.user):
            raise app_commands.CheckFailure("Only **Administrators** can use this command.")
        if not _manage_perm_ok(interaction.guild):
            raise app_commands.CheckFailure("I’m missing the **Manage Emojis and Stickers** permission.")


async def setup(bot: commands.Bot):
    await bot.add_cog(EmojisCog(bot))
