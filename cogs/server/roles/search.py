from __future__ import annotations
import re
from typing import List, Optional, Tuple
import discord
from configs.config_roles import ALMIGHTY_ROLE_ID
from .formatting import normalize, send_embed

# --- Fuzzy helpers ------------------------------------------------------------

try:
    from rapidfuzz import fuzz as _fuzz

    def _fuzzy(a: str, b: str) -> int:
        # robust to partials and token order (0–100)
        return max(_fuzz.partial_ratio(a, b), _fuzz.token_set_ratio(a, b))
except Exception:
    from difflib import SequenceMatcher

    def _fuzzy(a: str, b: str) -> int:
        # 0–100 like rapidfuzz
        return int(100 * SequenceMatcher(None, a, b).ratio())

def _score(q: str, name: str) -> int:
    """
    Composite score:
    - Very high weights for obvious hits
    - Otherwise, fall back to fuzzy similarity (0–100)
    """
    if q == name:
        return 1000
    if name.startswith(q) or name.endswith(q) or q in name:
        return 900
    if q.startswith(name) or q.endswith(name):
        return 850
    return _fuzzy(q, name)

# --- Role picking -------------------------------------------------------------

def _best_role(guild: discord.Guild, query: str) -> Tuple[Optional[discord.Role], List[Tuple[discord.Role, int]]]:
    qn = normalize(query)
    ranked: List[Tuple[discord.Role, int]] = []
    for role in guild.roles:
        if role.is_default() or role.id == ALMIGHTY_ROLE_ID:
            continue
        rn = normalize(role.name)
        s = _score(qn, rn)
        if s:
            ranked.append((role, s))
    ranked.sort(key=lambda x: (x[1], x[0].position), reverse=True)
    return (ranked[0][0] if ranked else None, ranked)

def _line(member: discord.Member) -> str:
    return f"{member.mention} — {member.display_name}"

# --- UI: pager + locate modal -------------------------------------------------

class _GotoPageModal(discord.ui.Modal):
    def __init__(self, pager: "MemberPager"):
        super().__init__(title="Go to page", timeout=60)
        self.pager = pager
        self.page_input = discord.ui.TextInput(
            label="Page number",
            placeholder=f"1–{max(1, len(self.pager.pages))}",
            min_length=1,
            max_length=4,
            required=True,
        )
        self.add_item(self.page_input)

    async def on_submit(self, itx: discord.Interaction):
        try:
            n = int(str(self.page_input.value).strip())
            if 1 <= n <= len(self.pager.pages):
                self.pager.index = n - 1
        except ValueError:
            pass

        # Defer and update the original message the view is attached to
        await itx.response.defer()
        if getattr(self.pager, "msg", None):
            await self.pager.msg.edit(embed=self.pager._embed(), view=self.pager)

class MemberPager(discord.ui.View):
    def __init__(self, pages: List[List[str]], *, title: str, icon: str = "🧑‍🤝‍🧑", timeout: float = 120):
        super().__init__(timeout=timeout)
        self.pages, self.index, self.title, self.icon = pages, 0, title, icon
        self.msg: Optional[discord.Message] = None  # set after sending

    def _embed(self) -> discord.Embed:
        total = len(self.pages)
        desc = "\n".join(self.pages[self.index]) if self.pages else "_No members found_"
        e = discord.Embed(title=f"{self.icon} {self.title}", description=desc, color=discord.Color.blurple())
        if total > 1:
            e.set_footer(text=f"Page {self.index+1}/{total} • Use ◀️ ▶️ or 🧭 Locate")
        return e

    async def _update(self, itx: discord.Interaction):
        await itx.response.edit_message(embed=self._embed(), view=self)

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def prev(self, itx: discord.Interaction, _: discord.ui.Button):
        if self.pages:
            self.index = (self.index - 1) % len(self.pages)
        await self._update(itx)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, itx: discord.Interaction, _: discord.ui.Button):
        if self.pages:
            self.index = (self.index + 1) % len(self.pages)
        await self._update(itx)

    @discord.ui.button(emoji="🧭", label="Locate", style=discord.ButtonStyle.primary)
    async def locate(self, itx: discord.Interaction, _: discord.ui.Button):
        await itx.response.send_modal(_GotoPageModal(self))

# --- Command worker -----------------------------------------------------------

async def show_role_members(ctx, query: str):
    guild: discord.Guild = ctx.guild

    # Supports mention syntax or plain text name
    m = re.search(r"<@&(\d+)>", query)
    role = guild.get_role(int(m.group(1))) if m else None
    if role is None:
        role, ranked = _best_role(guild, query)
        if role is None:
            hints = "\n".join(f"• {r.name}" for r, _ in ranked[:5]) or "No close matches."
            e = discord.Embed(
                title="🔎 Role not found",
                description=f"I couldn't match **{query}**.\n{hints}",
                color=discord.Color.red(),
            )
            await send_embed(ctx, e)
            return

    members = sorted(
        (m for m in guild.members if (role in m.roles) and not m.bot),
        key=lambda x: x.display_name.casefold()
    )
    lines = [_line(m) for m in members]
    total = len(lines)

    # 10 per page as requested
    PER = 10
    pages = [lines[i:i + PER] for i in range(0, len(lines), PER)] or [[]]
    view = MemberPager(pages, title=f"Members with {role.name} ({total})")

    e = view._embed()
    e.add_field(name="Role", value=f"{role.mention} — ID `{role.id}`", inline=False)

    # send as webhook (returns a message if available)
    msg = await send_embed(ctx, e, view=view)
    try:
        view.msg = msg  # Keep a handle so the modal can edit it
    except Exception:
        pass
