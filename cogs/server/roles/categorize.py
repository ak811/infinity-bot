from __future__ import annotations
import re
from typing import Dict, Optional
from .constants import CATEGORY_ITEMS
from .formatting import normalize

# Build normalized exact-name → category map
NAME_TO_CATEGORY: Dict[str, str] = {
    normalize(n): cat
    for cat, names in CATEGORY_ITEMS.items()
    for n in names
}

def categorize_role(role_name: str) -> Optional[str]:
    norm = normalize(role_name)
    cat = NAME_TO_CATEGORY.get(norm)
    # Guard: only a *plain* "Moon" matches (avoid emoji-decorated variants)
    if norm == "moon" and not re.fullmatch(r"\s*moon\s*", role_name, flags=re.IGNORECASE):
        return None
    return cat
