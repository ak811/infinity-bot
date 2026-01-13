# cogs/server/emojis/builders.py
from __future__ import annotations
import discord
from typing import Dict, Iterable, List, Tuple

from .constants import COLOR_LISTS, COLOR_DETAILS
from .formatters import (
    emoji_url,
    sticker_url,
    created_at_from_snowflake,
)

Field = Tuple[str, str]  # (name, value)

# ---- limits & sizing --------------------------------------------------------

MAX_FIELDS = 25
MAX_FIELD_VALUE = 1024
MAX_EMBED_TOTAL = 6000
SAFETY_MARGIN = 200  # stop early to be safe with hidden JSON overhead
ROWS_PER_PAGE = 10   # default for list pages

def _estimated_len(title: str, description: str | None, fields: List[Field]) -> int:
    total = len(title) + (len(description) if description else 0)
    for n, v in fields:
        total += len(n) + len(v)
    return total

# ---- public API expected by other modules ---------------------------------

def make_fields_from_groups(groups: Dict[str, List[str]]) -> List[Field]:
    fields: List[Field] = []
    for cat, rows in groups.items():
        fields.extend(_chunk_category(cat, rows))
    return fields

def make_list_embeds(title: str, fields: List[Field]) -> List[discord.Embed]:
    embeds: List[discord.Embed] = []
    current = _new_list_embed(title)
    cur_fields: List[Field] = []

    def flush():
        nonlocal current, cur_fields
        if cur_fields:
            for n, v in cur_fields:
                current.add_field(name=n, value=v, inline=False)
            embeds.append(current)
        current = _new_list_embed(title)
        cur_fields = []

    for name, value in fields:
        if len(value) > MAX_FIELD_VALUE:
            value = value[:MAX_FIELD_VALUE - 1] + "…"

        would_overflow_fields = (len(cur_fields) + 1) > MAX_FIELDS
        projected_len = _estimated_len(title, current.description, cur_fields + [(name, value)])
        would_overflow_size = projected_len > (MAX_EMBED_TOTAL - SAFETY_MARGIN)

        if would_overflow_fields or would_overflow_size:
            flush()

        cur_fields.append((name, value))

    flush()
    return embeds

# ---- pagination that enforces "10 rows per page" for grouped lists ---------

def make_paged_group_list_embeds(title: str, groups: Dict[str, List[str]], *, rows_per_page: int = ROWS_PER_PAGE) -> List[discord.Embed]:
    """
    Build embeds where each page has at most `rows_per_page` total rows across all categories.
    Category headings are preserved; a page can include multiple categories, and categories can span pages.
    """
    # Build an iterator of (category, row) preserving category order
    cat_items: List[Tuple[str, str]] = []
    for cat, rows in groups.items():
        for r in rows:
            cat_items.append((cat, r))

    pages: List[discord.Embed] = []
    i = 0
    total = len(cat_items)

    while i < total:
        # Take up to N rows
        slice_items = cat_items[i:i + rows_per_page]
        i += rows_per_page

        # Regroup slice by category for nicer fields
        page_fields: List[Field] = []
        acc: Dict[str, List[str]] = {}
        for cat, row in slice_items:
            acc.setdefault(cat, []).append(row)
        for cat, rows in acc.items():
            page_fields.append((cat, "\n".join(rows)))

        # Use the same embed size guards as make_list_embeds
        ems = make_list_embeds(title, page_fields)
        page = ems[0]
        pages.append(page)

    # Add "Page X/Y" footers
    total_pages = max(1, len(pages))
    for idx, em in enumerate(pages, start=1):
        current_footer = em.footer.text if em.footer else None
        footer = f"Page {idx}/{total_pages}"
        if current_footer:
            footer = f"{current_footer} • {footer}"
        em.set_footer(text=footer)

    return pages

def make_emoji_detail(e: discord.Emoji) -> discord.Embed:
    url = emoji_url(e)
    created = created_at_from_snowflake(e.id)
    locked = bool(getattr(e, "roles", None))
    anim = "Yes" if getattr(e, "animated", False) else "No"

    em = discord.Embed(
        title=f":{'a' if e.animated else ''}{e.name}:  {e.name}",
        color=COLOR_DETAILS,
        description=f"[Open image]({url})",
    )
    em.add_field(name="ID", value=str(e.id), inline=True)
    em.add_field(name="Animated", value=anim, inline=True)
    em.add_field(name="Created", value=created.strftime("%Y-%m-%d %H:%M UTC"), inline=True)
    em.add_field(name="Restricted (roles)", value="Yes" if locked else "No", inline=True)
    em.set_image(url=url)
    return em

def make_sticker_detail(s: discord.GuildSticker) -> discord.Embed:
    url = sticker_url(s)
    fmt = getattr(s, "format", getattr(s, "format_type", None))
    fmt_name = str(fmt).split(".")[-1].upper() if fmt else "UNKNOWN"

    em = discord.Embed(
        title=f":{s.name}:  {s.name}",
        color=COLOR_DETAILS,
        description=f"[Open image]({url})" if url else None,
    )
    em.add_field(name="ID", value=str(getattr(s, "id", "N/A")), inline=True)
    em.add_field(name="Format", value=fmt_name, inline=True)
    if url:
        em.set_image(url=url)
    return em

# ---- NEW: One-sticker-per-page --------------------------------------------

def make_sticker_single_pages(title: str, stickers: List[discord.GuildSticker]) -> List[discord.Embed]:
    """
    Build pages where each page is a single embed showing one sticker image.
    """
    pages: List[discord.Embed] = []

    for s in stickers:
        url = sticker_url(s)
        fmt = getattr(s, "format", getattr(s, "format_type", None))
        fmt_name = str(fmt).split(".")[-1].upper() if fmt else "UNKNOWN"

        em = discord.Embed(
            title=f"{title} — :{s.name}:",
            color=COLOR_DETAILS if url else COLOR_LISTS,
            description=f"[Open image]({url})" if url else None,
        )
        if url:
            em.set_image(url=url)
        em.add_field(name="ID", value=str(getattr(s, "id", "N/A")), inline=True)
        em.add_field(name="Format", value=fmt_name, inline=True)
        pages.append(em)

    total = max(1, len(pages))
    if total == 0:
        em = discord.Embed(title=title, color=COLOR_LISTS, description="No stickers found.")
        em.set_footer(text="Page 1/1")
        return [em]

    for idx, em in enumerate(pages, start=1):
        current_footer = em.footer.text if em.footer else None
        footer = f"Page {idx}/{total}"
        if current_footer:
            footer = f"{current_footer} • {footer}"
        em.set_footer(text=footer)

    return pages

# ---- internals -------------------------------------------------------------

def _new_list_embed(title: str) -> discord.Embed:
    return discord.Embed(title=title, color=COLOR_LISTS)

def _chunk_category(cat: str, rows: Iterable[str]) -> List[Field]:
    MAX = MAX_FIELD_VALUE
    chunks: List[Field] = []
    buf: List[str] = []
    current_len = 0
    index = 0

    def flush():
        nonlocal buf, current_len, index
        if not buf:
            return
        name = cat if index == 0 else f"{cat} (cont.)"
        value = "\n".join(buf)
        chunks.append((name, value))
        buf = []
        current_len = 0
        index += 1

    for line in rows:
        add_len = len(line) + (1 if buf else 0)
        if current_len + add_len > MAX:
            flush()
        buf.append(line)
        current_len += len(line) + (1 if len(buf) > 1 else 0)

    flush()
    return chunks
