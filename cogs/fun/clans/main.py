# cogs/clans/main.py
import discord
from discord.ext import commands
from typing import Optional, List, Tuple

from . import storage
from .utils import slugify, pretty_name, sum_resources, EMOJI_COIN, EMOJI_ORB, EMOJI_STAR, EMOJI_DIAMOND, EMOJI_XP
from .views import PagedView
from datetime import datetime

# Optional: route through your pet-styled sender if you have it
try:
    from configs.helper import send_as_webhook
    async def send_embed(ctx, embed: discord.Embed, **kwargs):
        return await send_as_webhook(ctx, "clans", embed=embed, **kwargs)
except Exception:
    async def send_embed(ctx, embed: discord.Embed, **kwargs):
        return await ctx.send(embed=embed, **kwargs)

CLAN_COLOR = discord.Color.orange()
ERROR_COLOR = discord.Color.red()
OK_COLOR = discord.Color.green()
INFO_COLOR = discord.Color.blurple()

def fmt_user(guild: discord.Guild, uid: int) -> str:
    m = guild.get_member(uid)
    if m:
        # escape markdown so display names with *, _, etc. don’t mangle the embed
        safe = discord.utils.escape_markdown(m.display_name)
        return f"{m.mention} **{safe}**"
    return f"<@{uid}>"

def embed_clan_profile(ctx, slug: str, compact: bool = False) -> discord.Embed:
    clan = storage.get_clan(slug)
    if not clan:
        return discord.Embed(title="Clan not found", color=ERROR_COLOR, description="That clan no longer exists.")

    name = clan["name"]
    icon = clan.get("icon", "🏴")
    motto = clan.get("motto") or "_No motto set_"
    leader_id = clan["leader_id"]
    members = clan.get("members", [])

    sxp, scoins, sorbs, sstars, sdiam = sum_resources(members)

    DIAMOND_USD = 5 / 150
    STAR_USD = DIAMOND_USD / 10
    ORB_USD = DIAMOND_USD / 100
    COIN_USD = DIAMOND_USD / 1000

    def to_usd(coins: int, orbs: int, stars: int, diamonds: int) -> float:
                return (
                    coins * COIN_USD +
                    orbs * ORB_USD +
                    stars * STAR_USD +
                    diamonds * DIAMOND_USD
                )
    
    coins_usd    = to_usd(scoins, 0, 0, 0)
    orbs_usd     = to_usd(0, sorbs, 0, 0)
    stars_usd    = to_usd(0, 0, sstars, 0)
    diamonds_usd = to_usd(0, 0, 0, sdiam)
    total_usd    = coins_usd + orbs_usd + stars_usd + diamonds_usd

    # Format created_at if it exists
    raw_created = clan.get("created_at")
    created_fmt = "—"
    if raw_created:
        try:
            dt = datetime.fromisoformat(raw_created.replace("Z", "+00:00"))  # parse ISO string
            created_fmt = dt.strftime("%B %d, %Y at %H:%M:%S")  # e.g. July 27, 2025 at 08:04:43
        except Exception:
            created_fmt = raw_created

    e = discord.Embed(title=f"{icon} {name}", color=CLAN_COLOR)
    e.add_field(name="Leader", value=fmt_user(ctx.guild, leader_id), inline=True)
    e.add_field(name="Members", value=str(len(members)), inline=True)
    e.add_field(name="Created", value=created_fmt, inline=True)
    e.add_field(name="Motto", value=motto, inline=False)

    e.add_field(name=f"{EMOJI_XP} Total XP", value=f"{sxp:,}", inline=True)
    e.add_field(name=f"{EMOJI_COIN} Total Coins", value=f"{scoins:,}", inline=True)
    e.add_field(name=f"{EMOJI_ORB} Total Orbs", value=f"{sorbs:,}", inline=True)
    e.add_field(name=f"{EMOJI_STAR} Total Stars", value=f"{sstars:,}", inline=True)
    e.add_field(name=f"{EMOJI_DIAMOND} Total Diamonds", value=f"{sdiam:,}", inline=True)
    e.add_field(name="💵 Total Dollars", value=f"**${total_usd:,.2f}**", inline=True)


    if not compact:
        preview = []
        for uid in members[:20]:
            tag = " 👑" if uid == leader_id else ""
            preview.append(f"- {fmt_user(ctx.guild, uid)}{tag}")
        extra = "" if len(members) <= 20 else f"\n…and {len(members)-20} more. Use `!clan members`."
        e.add_field(name="Roster", value="\n".join(preview) + extra if preview else "_Empty_", inline=False)

    return e

def format_rank_row(n: int, icon: str, name: str, members: int, xp: int) -> str:
    idx = f"#{n}".rjust(3)
    return f"{idx} {icon} **{name}** — {members} members • {xp:,} XP"

def build_clan_help_embed(prefix: str = "!") -> discord.Embed:
    desc = (
        "**⚔️ Basics**\n"
        f"• 🎪 `{prefix}clan profile` or `{prefix}clan p` — your clan profile\n"
        f"• 🔍 `{prefix}clan profile <name>` — view another clan\n"
        f"• 🏗️ `{prefix}clan create <name>` — create a clan\n"
        f"• 🤝 `{prefix}clan join <name>` — join a clan\n"
        f"• 🏃 `{prefix}clan leave` — leave your clan\n"
        f"• 👥 `{prefix}clan members` — list members\n"
        f"• 🏆 `{prefix}clan top` — leaderboard by combined XP\n\n"
        "**👑 Leader Only**\n"
        f"• ✨ `{prefix}clan set motto <text>` — set clan motto\n"
        f"• 🎭 `{prefix}clan set icon <emoji>` — set clan icon\n"
        f"• 📝 `{prefix}clan rename <new name>` or `{prefix}clan rn <new name>` — rename the clan\n"
        f"• 🎖️ `{prefix}clan transfer @user` — transfer leadership\n"
        f"• 💀 `{prefix}clan disband` — disband your clan\n\n"
    )
    return discord.Embed(title="🎪 Clan Commands", description=desc, color=CLAN_COLOR)

class ClanCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await storage.load()

    # Group: now shows help when invoked without subcommand; alias: "clans"
    @commands.group(name="clan", aliases=["clans"], invoke_without_command=True)
    async def clan_group(self, ctx: commands.Context):
        """Show clan command list."""
        await storage.load()
        await send_embed(ctx, build_clan_help_embed(prefix="!"))

    # --- Profile ---
    @clan_group.command(name="profile", aliases=["p"])
    async def clan_profile(self, ctx: commands.Context, *, name: Optional[str] = None):
        """Show your clan profile, or a specific clan by name."""
        await storage.load()
        slug = slugify(name) if name else storage.get_user_clan_slug(ctx.author.id)
        if slug is None:
            await send_embed(ctx, discord.Embed(
                title="You're not in a clan",
                color=INFO_COLOR,
                description="Create one with `!clan create <name>` or join with `!clan join <name>`."
            ))
            return
        if not storage.get_clan(slug):
            await send_embed(ctx, discord.Embed(title="Clan not found", color=ERROR_COLOR))
            return
        await send_embed(ctx, embed_clan_profile(ctx, slug))

    # --- Create ---
    @clan_group.command(name="create")
    async def clan_create(self, ctx: commands.Context, *, name: str):
        """Create a clan (you become the leader)."""
        await storage.load()
        if storage.is_user_in_clan(ctx.author.id):
            await send_embed(ctx, discord.Embed(
                title="You’re already in a clan",
                color=ERROR_COLOR,
                description="Leave your current clan with `!clan leave` before creating a new one."
            ))
            return
        slug = slugify(name)
        if not slug:  # empty string means invalid after slugify
            await send_embed(ctx, discord.Embed(
                title="Invalid clan name",
                color=ERROR_COLOR,
                description="Pick a name with letters or numbers."
            ))
            return
        pname = pretty_name(name)
        try:
            storage.create_clan(slug, pname, ctx.author.id)
        except ValueError:
            await send_embed(ctx, discord.Embed(title="Clan name taken", color=ERROR_COLOR, description="Pick a different name."))
            return
        await send_embed(ctx, discord.Embed(
            title="Clan created!",
            description=f"Welcome to **{pname}**.\nYou are the **leader** 👑",
            color=OK_COLOR,
        ))

    # --- Join ---
    @clan_group.command(name="join")
    async def clan_join(self, ctx: commands.Context, *, name: str):
        """Join an existing clan."""
        await storage.load()
        if storage.is_user_in_clan(ctx.author.id):
            await send_embed(ctx, discord.Embed(
                title="You’re already in a clan",
                color=ERROR_COLOR,
                description="Leave your current clan with `!clan leave` first."
            ))
            return
        slug = slugify(name)
        clan = storage.get_clan(slug)
        if not clan:
            await send_embed(ctx, discord.Embed(title="Clan not found", color=ERROR_COLOR))
            return
        storage.join_clan(slug, ctx.author.id)
        await send_embed(ctx, discord.Embed(
            title="Joined clan",
            description=f"You joined **{clan['name']}** {clan.get('icon','🏴')}",
            color=OK_COLOR,
        ))

    # --- Leave ---
    @clan_group.command(name="leave")
    async def clan_leave(self, ctx: commands.Context):
        """Leave your current clan."""
        await storage.load()
        slug = storage.get_user_clan_slug(ctx.author.id)
        if slug is None:
            await send_embed(ctx, discord.Embed(title="Not in a clan", color=ERROR_COLOR))
            return
        clan = storage.get_clan(slug)
        if clan and clan["leader_id"] == ctx.author.id and len(clan["members"]) > 1:
            await send_embed(ctx, discord.Embed(
                title="Leader cannot leave",
                description="Transfer leadership with `!clan transfer @user` or disband with `!clan disband`.",
                color=ERROR_COLOR,
            ))
            return
        storage.leave_clan(ctx.author.id)
        await send_embed(ctx, discord.Embed(title="You left the clan", color=OK_COLOR))

    # --- Members list ---
    @clan_group.command(name="members")
    async def clan_members(self, ctx: commands.Context, *, name: Optional[str] = None):
        """Show the members of a clan (defaults to your clan)."""
        await storage.load()
        slug = slugify(name) if name else storage.get_user_clan_slug(ctx.author.id)
        if slug is None:
            await send_embed(ctx, discord.Embed(title="Clan not found", color=ERROR_COLOR))
            return
        clan = storage.get_clan(slug)
        if not clan:
            await send_embed(ctx, discord.Embed(title="Clan not found", color=ERROR_COLOR))
            return

        members = clan["members"]
        leader_id = clan["leader_id"]
        lines = []
        for uid in members:
            tag = " 👑" if uid == leader_id else ""
            m = ctx.guild.get_member(uid)
            lines.append(f"- {fmt_user(ctx.guild, uid)}{tag}")

        pages: List[discord.Embed] = []
        CHUNK = 20
        for i in range(0, len(lines), CHUNK):
            chunk = "\n".join(lines[i:i+CHUNK]) or "_No members_"
            e = discord.Embed(
                title=f"{clan.get('icon','🏴')} {clan['name']} — Members",
                description=chunk,
                color=CLAN_COLOR,
            )
            pages.append(e)

        if len(pages) == 1:
            await send_embed(ctx, pages[0])
        else:
            view = PagedView(pages)
            await ctx.send(embed=view.current(), view=view)

    # --- Top leaderboard by combined XP ---
    @clan_group.command(name="top")
    async def clan_top(self, ctx: commands.Context):
        """Show top clans by combined XP."""
        await storage.load()
        clans = storage.list_clans()
        rows: List[Tuple[str, int, int, str, str]] = []

        for slug, clan in clans.items():
            members = clan.get("members", [])
            sxp, _, _, _, _ = sum_resources(members)
            rows.append((slug, sxp, len(members), clan.get("icon", "🏴"), clan["name"]))

        rows.sort(key=lambda t: t[1], reverse=True)
        lines = [format_rank_row(i+1, icon, name, mems, xp) for i, (slug, xp, mems, icon, name) in enumerate(rows)]
        if not lines:
            await send_embed(ctx, discord.Embed(title="No clans yet", color=INFO_COLOR))
            return

        pages: List[discord.Embed] = []
        CHUNK = 10
        for i in range(0, len(lines), CHUNK):
            chunk = "\n".join(lines[i:i+CHUNK])
            e = discord.Embed(title="🏆 Top Clans", description=chunk, color=CLAN_COLOR)
            pages.append(e)

        if len(pages) == 1:
            await send_embed(ctx, pages[0])
        else:
            view = PagedView(pages)
            await ctx.send(embed=view.current(), view=view)

    # --- Set motto/icon (leader only) ---
    @clan_group.command(name="set")
    async def clan_set(self, ctx: commands.Context, field: str, *, value: str):
        """Leader tools: !clan set motto <text> | !clan set icon <emoji>"""
        await storage.load()
        slug = storage.get_user_clan_slug(ctx.author.id)
        if slug is None:
            await send_embed(ctx, discord.Embed(title="Not in a clan", color=ERROR_COLOR))
            return
        clan = storage.get_clan(slug)
        if clan["leader_id"] != ctx.author.id:
            await send_embed(ctx, discord.Embed(title="Leader only", color=ERROR_COLOR))
            return

        field = field.lower()
        try:
            if field == "motto":
                storage.set_motto(slug, value)
                await send_embed(ctx, discord.Embed(title="Motto updated", color=OK_COLOR))
            elif field == "icon":
                storage.set_icon(slug, value.strip().split()[0])
                await send_embed(ctx, discord.Embed(title="Icon updated", color=OK_COLOR))
            else:
                await send_embed(ctx, discord.Embed(title="Unknown field", description="Use `motto` or `icon`.", color=ERROR_COLOR))
        except ValueError as e:
            await send_embed(ctx, discord.Embed(title="Error", description=str(e), color=ERROR_COLOR))

    # --- Rename (leader only) ---
    @clan_group.command(name="rename", aliases=["rn"])
    async def clan_rename(self, ctx: commands.Context, *, new_name: str):
        """Rename your clan (leader only)."""
        await storage.load()
        slug = storage.get_user_clan_slug(ctx.author.id)
        if slug is None:
            await send_embed(ctx, discord.Embed(title="Not in a clan", color=ERROR_COLOR))
            return
        clan = storage.get_clan(slug)
        if clan["leader_id"] != ctx.author.id:
            await send_embed(ctx, discord.Embed(title="Leader only", color=ERROR_COLOR))
            return

        new_slug = slugify(new_name)
        if not new_slug:
            await send_embed(ctx, discord.Embed(
                title="Invalid clan name",
                color=ERROR_COLOR,
                description="Pick a name with letters or numbers."
            ))
            return
        try:
            storage.rename_clan(slug, new_slug, pretty_name(new_name))
        except ValueError as e:
            await send_embed(ctx, discord.Embed(title="Error", description=str(e), color=ERROR_COLOR))
            return

        await send_embed(ctx, discord.Embed(
            title="Clan renamed!",
            description=f"Your clan is now called **{pretty_name(new_name)}**.",
            color=OK_COLOR,
        ))

    # --- Transfer leadership (leader only) ---
    @clan_group.command(name="transfer")
    async def clan_transfer(self, ctx: commands.Context, member: discord.Member):
        await storage.load()
        slug = storage.get_user_clan_slug(ctx.author.id)
        if slug is None:
            await send_embed(ctx, discord.Embed(title="Not in a clan", color=ERROR_COLOR))
            return
        clan = storage.get_clan(slug)
        if clan["leader_id"] != ctx.author.id:
            await send_embed(ctx, discord.Embed(title="Leader only", color=ERROR_COLOR))
            return
        if member.id not in clan["members"]:
            await send_embed(ctx, discord.Embed(title="User not in your clan", color=ERROR_COLOR))
            return

        storage.transfer_leader(slug, member.id)
        await send_embed(ctx, discord.Embed(
            title="Leadership transferred",
            description=f"👑 {member.mention} is now the leader.",
            color=OK_COLOR,
        ))

    # --- Disband (leader only) ---
    @clan_group.command(name="disband")
    async def clan_disband(self, ctx: commands.Context):
        await storage.load()
        slug = storage.get_user_clan_slug(ctx.author.id)
        if slug is None:
            await send_embed(ctx, discord.Embed(title="Not in a clan", color=ERROR_COLOR))
            return
        clan = storage.get_clan(slug)
        if clan["leader_id"] != ctx.author.id:
            await send_embed(ctx, discord.Embed(title="Leader only", color=ERROR_COLOR))
            return

        storage.disband(slug)
        await send_embed(ctx, discord.Embed(title="Clan disbanded", color=OK_COLOR))

# --- setup ---
async def setup(bot: commands.Bot):
    await bot.add_cog(ClanCog(bot))
