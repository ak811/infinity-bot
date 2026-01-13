# cogs/clans/utils.py
import re
from typing import Tuple, Iterable

# ---------- Slug/Name helpers ----------
def slugify(name: str) -> str:
    """
    Convert a name into a lowercase slug (safe for keys).
    Example: "My Clan Name!" -> "my-clan-name"
    """
    s = name.lower()
    s = re.sub(r"[^a-z0-9\s-]+", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s[:40]  # limit length

def pretty_name(name: str) -> str:
    """
    Clean up spacing and capitalization for display.
    Example: "my clan   name" -> "My Clan Name"
    """
    return re.sub(r"\s+", " ", name).strip().title()

# ---------- Emoji labels ----------
EMOJI_XP = "🌟"
EMOJI_COIN = "🪙"
EMOJI_ORB = "🔮"
EMOJI_STAR = "⭐"
EMOJI_DIAMOND = "💎"

# ---------- Economy getters / updaters ----------
# Import your real functions from leaderboards/main.py
from cogs.economy.coin.service import get_total_coins
from cogs.economy.orb.service import get_total_orbs
from cogs.economy.diamond.service import get_total_diamonds
from cogs.economy.star.service import get_total_stars
\
from cogs.economy.xp.service import get_total_xp

# ---------- Resource helpers ----------
def get_user_resources(user_id: int) -> Tuple[int, int, int, int, int]:
    """
    Returns (xp, coins, orbs, stars, diamonds) for a user.
    Uses functions from leaderboards.main.
    """
    xp = int(get_total_xp(user_id))
    coins = int(get_total_coins(user_id))
    orbs = int(get_total_orbs(user_id))
    stars = int(get_total_stars(user_id))
    diamonds = int(get_total_diamonds(user_id))
    return xp, coins, orbs, stars, diamonds

def sum_resources(user_ids: Iterable[int]) -> Tuple[int, int, int, int, int]:
    """
    Sum resources across multiple user IDs.
    Returns combined totals (xp, coins, orbs, stars, diamonds).
    """
    sxp = scoins = sorbs = sstars = sdiam = 0
    for uid in user_ids:
        xp, c, o, s, d = get_user_resources(uid)
        sxp += xp
        scoins += c
        sorbs += o
        sstars += s
        sdiam += d
    return sxp, scoins, sorbs, sstars, sdiam
