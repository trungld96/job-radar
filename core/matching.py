from __future__ import annotations

import re
from functools import lru_cache


@lru_cache(maxsize=4096)
def _pattern(keyword: str) -> re.Pattern:
    """Word-boundary regex; keyword should already be lowercased."""
    return re.compile(r"(?<!\w)" + re.escape(keyword) + r"(?!\w)", re.IGNORECASE)


def matches(text: str, keyword: str) -> bool:
    """Substring match with word boundaries — avoids 'rag' matching 'storage'."""
    return bool(_pattern(keyword).search(text))
