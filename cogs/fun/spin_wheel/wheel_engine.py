"""
Wheel outcome engine (equal probability per slot).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict
import random

from .config_spin import WHEEL, VALUE

@dataclass(frozen=True)
class Outcome:
    kind: str  # "payout" | "respin" | "multiplier"
    label: str
    currency: Optional[str] = None
    amount: Optional[int] = None
    payouts: Optional[Dict[str, int]] = None  # multi-currency payouts
    entry_index: int = 0

    def is_payout(self) -> bool:
        return self.kind == "payout" and (self.payouts is not None or (self.currency is not None and self.amount is not None))

    def coin_value(self) -> int:
        if not self.is_payout():
            return 0
        if self.payouts:
            return sum(VALUE[c] * int(a) for c, a in self.payouts.items())
        return VALUE[self.currency] * int(self.amount)

def _pick_index(rng: random.Random) -> int:
    return rng.randrange(len(WHEEL))

def spin_once(rng: Optional[random.Random] = None) -> Outcome:
    rng = rng or random
    idx = _pick_index(rng)
    e = WHEEL[idx]

    if e.kind == "respin":
        return Outcome(kind="respin", label=e.label, entry_index=idx)
    if e.kind == "multiplier":
        return Outcome(kind="multiplier", label=e.label, entry_index=idx)
    # payout (single or combo)
    if e.payouts:
        return Outcome(kind="payout", label=e.label, payouts=e.payouts, entry_index=idx)
    return Outcome(kind="payout", label=e.label, currency=e.currency, amount=e.amount, entry_index=idx)

# (Optional legacy helpers preserved)
def prize_labels_tape(shuffle: bool = True, rng: Optional[random.Random] = None) -> List[str]:
    rng = rng or random
    labels = [e.label for e in WHEEL]
    if shuffle:
        rng.shuffle(labels)
    return labels
