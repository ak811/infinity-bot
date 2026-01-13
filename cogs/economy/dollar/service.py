# cogs/economy/dollar/service.py
from __future__ import annotations
from importlib import import_module

# Conversion (legacy rule)
DIAMOND_USD = 5 / 150          # ≈ 0.033333...
STAR_USD    = DIAMOND_USD / 10 # ≈ 0.003333...
ORB_USD     = DIAMOND_USD / 100
COIN_USD    = DIAMOND_USD / 1000

def _to_usd(coins=0, orbs=0, stars=0, diamonds=0) -> float:
    return coins*COIN_USD + orbs*ORB_USD + stars*STAR_USD + diamonds*DIAMOND_USD

def get_total_dollars(user_id: int | str, *, round_to_cents: bool = True, return_breakdown: bool = False):
    # Lazy import to avoid circulars
    coins_mod    = import_module("cogs.economy.coin.service")
    orbs_mod     = import_module("cogs.economy.orb.service")
    stars_mod    = import_module("cogs.economy.star.service")
    diamonds_mod = import_module("cogs.economy.diamond.service")

    uid = str(user_id)
    coins    = coins_mod.get_total_coins(uid)
    orbs     = orbs_mod.get_total_orbs(uid)
    stars    = stars_mod.get_total_stars(uid)
    diamonds = diamonds_mod.get_total_diamonds(uid)

    coins_usd    = _to_usd(coins=coins)
    orbs_usd     = _to_usd(orbs=orbs)
    stars_usd    = _to_usd(stars=stars)
    diamonds_usd = _to_usd(diamonds=diamonds)
    total_usd    = coins_usd + orbs_usd + stars_usd + diamonds_usd

    if round_to_cents:
        total_usd = round(total_usd + 1e-12, 2)

    if return_breakdown:
        return {
            "total": total_usd,
            "coins": round(coins_usd, 2) if round_to_cents else coins_usd,
            "orbs": round(orbs_usd, 2) if round_to_cents else orbs_usd,
            "stars": round(stars_usd, 2) if round_to_cents else stars_usd,
            "diamonds": round(diamonds_usd, 2) if round_to_cents else diamonds_usd,
        }
    return total_usd
