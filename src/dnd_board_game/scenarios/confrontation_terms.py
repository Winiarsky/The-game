"""Player-facing names for the same confrontation effect in different contexts."""
from __future__ import annotations
import re


def effect_name(kind: str) -> str:
    return 'Postęp' if kind == 'object' else 'Wpływ'


def effect_text(text: str, kind: str | None) -> str:
    """Adapt canonical/legacy labels without changing saved mechanics or logs.

    None denotes a shared reference applicable to both NPCs and objects.
    Call once on source text, not on already formatted presentation.
    """
    if kind == 'npc':
        return text
    forms = {'wpływu': 'postępu', 'Wpływ': 'Postęp', 'wpływ': 'postęp'}
    return re.sub(r'\b(wpływu|Wpływ|wpływ)\b',
                  lambda m: f'{m[0]} / {forms[m[0]]}' if kind is None else forms[m[0]], text)
