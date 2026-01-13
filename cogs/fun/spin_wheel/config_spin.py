"""
Spin-the-Wheel configuration & math helpers.

- Entry fee, cooldown, animation tuning
- Currency values & emojis
- Prize table with **equal probability per slot**
- EV helpers (equal-probability math), including combo payouts
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Optional

# ==== Import your project's emoji config if available ====
try:
    from configs.config_general import (
        COIN_EMOJI as _COIN,
        ORB_EMOJI as _ORB,
        STAR_EMOJI as _STAR,
        DIAMOND_EMOJI as _DIA,
    )
except Exception:
    _COIN, _ORB, _STAR, _DIA = "🪙", "🟣", "⭐", "💎"

# ==== Public Emojis map ====
EMOJI: Dict[str, str] = {
    "coins": _COIN,
    "orbs": _ORB,
    "stars": _STAR,
    "diamonds": _DIA,
}

# ==== Currency values (for EV math) ====
VALUE: Dict[str, int] = {
    "coins": 1,
    "orbs": 10,
    "stars": 100,
    "diamonds": 1000,
}

# ==== Gameplay knobs ====
ENTRY_FEE_COINS: int = 100
SPIN_COOLDOWN_SECONDS: int = 0
MAX_CHAINED_SPINS: int = 3

# ===== Animation tuning (FAST defaults; pairs with deterministic view) =====
ROTATION_LOOPS: int = 0
EXTRA_TICKS_AFTER_LOOPS: int = 2
ANIMATION_MIN_DELAY = 0.004
ANIMATION_MAX_DELAY = 0.12

# ===== Prize table definition =====
# Equal probability per slot. Includes single-currency payouts and combo payouts.

@dataclass(frozen=True)
class WheelEntry:
    label: str
    kind: str  # "payout" | "respin" | "multiplier"
    currency: Optional[str] = None       # for single payout
    amount: Optional[int] = None         # for single payout
    payouts: Optional[Dict[str, int]] = None  # for combo payout (e.g., {"coins": 40, "orbs": 2})
    weight: int = 1  # unused in equal-probability mode

def L_coins(x:int) -> str: return f"{EMOJI['coins']} {x} Coins"
def L_orbs(x:int)  -> str: return f"{EMOJI['orbs']} {x} Orbs"
def L_star(x:int)  -> str: return f"{EMOJI['stars']} {x} Star" + ("s" if x!=1 else "")
def L_combo(d:Dict[str,int]) -> str:
    parts = []
    if d.get("coins"):    parts.append(L_coins(d["coins"]))
    if d.get("orbs"):     parts.append(L_orbs(d["orbs"]))
    if d.get("stars"):    parts.append(L_star(d["stars"]))
    if d.get("diamonds"): parts.append(f"{EMOJI['diamonds']} {d['diamonds']} Diamond" + ("s" if d['diamonds']!=1 else ""))
    return " + ".join(parts)

# — 36 slots: anchors, specials, singles, and a dozen combos —
WHEEL: List[WheelEntry] = [
    # High anchors & specials spaced around the wheel
    WheelEntry(label=f"{EMOJI['diamonds']} 1 Diamond", kind="payout", currency="diamonds", amount=1),         # 0
    WheelEntry(label=L_orbs(10), kind="payout", currency="orbs", amount=10),                                  # 1
    WheelEntry(label=L_coins(300), kind="payout", currency="coins", amount=300),                               # 2
    WheelEntry(label=L_star(3), kind="payout", currency="stars", amount=3),                                    # 3
    WheelEntry(label=L_orbs(7), kind="payout", currency="orbs", amount=7),                                     # 4
    WheelEntry(label=L_coins(150), kind="payout", currency="coins", amount=150),                                # 5
    WheelEntry(label="🎟 Free Spin Token", kind="respin"),                                                      # 6
    WheelEntry(label=L_orbs(4), kind="payout", currency="orbs", amount=4),                                     # 7
    WheelEntry(label=L_coins(80), kind="payout", currency="coins", amount=80),                                  # 8
    WheelEntry(label="⚡ 2× Multiplier", kind="multiplier"),                                                    # 9

    # Singles & smalls
    WheelEntry(label=L_orbs(2), kind="payout", currency="orbs", amount=2),                                     # 10
    WheelEntry(label=L_coins(40), kind="payout", currency="coins", amount=40),                                  # 11
    WheelEntry(label=L_star(2), kind="payout", currency="stars", amount=2),                                    # 12
    WheelEntry(label=L_orbs(6), kind="payout", currency="orbs", amount=6),                                     # 13
    WheelEntry(label=L_coins(20), kind="payout", currency="coins", amount=20),                                  # 14
    WheelEntry(label="🎟 Free Spin Token", kind="respin"),                                                      # 15
    WheelEntry(label=L_orbs(9), kind="payout", currency="orbs", amount=9),                                     # 16
    WheelEntry(label="🙅 Nothing", kind="payout", currency="coins", amount=0),                                  # 17
    WheelEntry(label=L_orbs(3), kind="payout", currency="orbs", amount=3),                                     # 18
    WheelEntry(label=L_coins(10), kind="payout", currency="coins", amount=10),                                  # 19
    WheelEntry(label=L_star(1), kind="payout", currency="stars", amount=1),                                    # 20
    WheelEntry(label=L_orbs(5), kind="payout", currency="orbs", amount=5),                                     # 21
    WheelEntry(label="⚡ 2× Multiplier", kind="multiplier"),                                                    # 22
    WheelEntry(label=L_orbs(8), kind="payout", currency="orbs", amount=8),                                     # 23
    WheelEntry(label=L_orbs(1), kind="payout", currency="orbs", amount=1),                                     # 24

    # — Combos (12) —
    WheelEntry(label=L_combo({"coins":20,  "orbs":1}), payouts={"coins":20,  "orbs":1}, kind="payout"),        # 25 (30 coins EV)
    WheelEntry(label=L_combo({"coins":40,  "orbs":2}), payouts={"coins":40,  "orbs":2}, kind="payout"),        # 26 (60)
    WheelEntry(label=L_combo({"coins":80,  "orbs":1}), payouts={"coins":80,  "orbs":1}, kind="payout"),        # 27 (90)
    WheelEntry(label=L_combo({"coins":150, "orbs":2}), payouts={"coins":150, "orbs":2}, kind="payout"),        # 28 (170)
    WheelEntry(label=L_combo({"coins":10,  "orbs":3}), payouts={"coins":10,  "orbs":3}, kind="payout"),        # 29 (40)
    WheelEntry(label=L_combo({"stars":1,   "orbs":1}), payouts={"stars":1,   "orbs":1}, kind="payout"),        # 30 (110)
    WheelEntry(label=L_combo({"stars":2,   "orbs":1}), payouts={"stars":2,   "orbs":1}, kind="payout"),        # 31 (210)
    WheelEntry(label=L_combo({"orbs":3,    "coins":20}), payouts={"orbs":3,  "coins":20}, kind="payout"),      # 32 (50)
    WheelEntry(label=L_combo({"orbs":5,    "coins":10}), payouts={"orbs":5,  "coins":10}, kind="payout"),      # 33 (60)
    WheelEntry(label=L_combo({"orbs":9,    "coins":20}), payouts={"orbs":9,  "coins":20}, kind="payout"),      # 34 (110)
    WheelEntry(label=L_combo({"orbs":4,    "coins":40}), payouts={"orbs":4,  "coins":40}, kind="payout"),      # 35 (80)
]

# ===== EV helpers (equal-probability) =====
def coin_value_of(currency: str, amount: int) -> int:
    return VALUE[currency] * amount

def base_expected_value() -> float:
    """Expected payout per draw (no re-spins; equal probability per slot)."""
    n = max(1, len(WHEEL))
    p = 1.0 / n
    ev = 0.0
    for e in WHEEL:
        if e.kind != "payout":
            continue
        if e.payouts:
            ev += p * sum(VALUE[c] * int(a) for c, a in e.payouts.items())
        elif e.currency and e.amount is not None:
            ev += p * coin_value_of(e.currency, int(e.amount))
    return ev

def respin_probability() -> float:
    n = max(1, len(WHEEL))
    return sum(1 for e in WHEEL if e.kind == "respin") / n

def infinite_chain_ev() -> float:
    base = base_expected_value()
    p_r = respin_probability()
    if p_r >= 1.0:
        return float("inf")
    return base / (1.0 - p_r)

def capped_chain_ev(max_chained_spins: int = MAX_CHAINED_SPINS) -> float:
    base = base_expected_value()
    p_r = respin_probability()
    if p_r == 0.0:
        return base
    factor = (1.0 - (p_r ** max_chained_spins)) / (1.0 - p_r)
    return base * factor

def house_edge(ev_coins: float, entry_fee: int = ENTRY_FEE_COINS) -> float:
    return max(0.0, (entry_fee - ev_coins) / entry_fee)

if __name__ == "__main__":
    base = base_expected_value()
    p_r = respin_probability()
    inf_ev = infinite_chain_ev()
    cap_ev = capped_chain_ev()
    print(f"Base EV (no re-spins): {base:.2f} coins")
    print(f"Re-Spin probability:   {p_r*100:.2f}%")
    print(f"Infinite-chain EV:     {inf_ev:.2f} coins (edge ~{house_edge(inf_ev)*100:.2f}%)")
    print(f"Capped({MAX_CHAINED_SPINS}) EV: {cap_ev:.2f} coins (edge ~{house_edge(cap_ev)*100:.2f}%)")
