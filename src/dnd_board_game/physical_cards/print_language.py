"""Safe keyword emphasis for printable rules; never changes rules or numbers."""
from __future__ import annotations

from html import escape
import re
from collections.abc import Iterable


def keyword_text(text: str, terms: Iterable[str]) -> str:
    """Emphasize whole terms, longest first, escaping all user-authored text."""
    ordered = sorted(set(terms), key=len, reverse=True)
    if not ordered:
        return escape(text)
    pattern = re.compile(r'(?<!\w)(?:' + '|'.join(re.escape(t) for t in ordered) + r')(?!\w)', re.IGNORECASE)
    chunks: list[str] = []
    start = 0
    for match in pattern.finditer(text):
        chunks.extend((escape(text[start:match.start()]), '<strong class="keyword">' + escape(match.group()) + '</strong>'))
        start = match.end()
    chunks.append(escape(text[start:]))
    return ''.join(chunks)
