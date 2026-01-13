# cogs/nickname/levels.py
from typing import Optional, Tuple, Sequence

def compute_level_and_next_threshold(
    xp: int,
    roles: Sequence[tuple]
) -> Tuple[int, Optional[int]]:
    """
    roles: sequence of (role_id, min_xp, max_xp)
    Level mapping:
      - Level 1: below first role's min_xp
      - Level 2..(len(roles)+1): 1 + index of highest role min_xp satisfied
    Returns (level, next_threshold_min_xp or None if at max).
    """
    level = 1  # newcomer default
    highest_idx = -1
    for idx, (_, min_xp, _) in enumerate(roles):
        if xp >= int(min_xp):
            highest_idx = idx
            level = idx + 2  # Skilled should be L2
        else:
            break

    next_threshold = None
    if highest_idx + 1 < len(roles):
        next_threshold = int(roles[highest_idx + 1][1])

    return level, next_threshold
