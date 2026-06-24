from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class ReactiveMixin:
    """Mixin zarządzający reakcjami (np. Opportunity Attack)."""

    reactions_max: int = 1
    reactions_left: int = 1
    reactions: List[object] = field(default_factory=list)

    def reset_reactions(self) -> None:
        self.reactions_left = max(0, int(self.reactions_max))

    def can_react(self) -> bool:
        return self.reactions_left > 0 and bool(self.reactions)

    def consume_reaction(self) -> bool:
        if self.reactions_left <= 0:
            return False
        self.reactions_left -= 1
        return True
