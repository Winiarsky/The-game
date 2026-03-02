from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ReactionContext(Protocol):
    game: Any
    event: dict[str, Any]


@dataclass
class Reaction:
    """Bazowa reakcja – implementuj triggers() i execute()."""

    id: str
    label: str
    priority: int = 0
    action_cost: int = 1
    requires_reach: bool = True
    blocks_range_attacker: bool = True

    def triggers(self, actor, event: dict[str, Any]) -> bool:  # pragma: no cover - interfejs
        raise NotImplementedError

    def reason(self, actor, event: dict[str, Any]) -> str:
        """Opis dlaczego można zareagować (do promptu)."""
        return self.label

    def execute(self, actor, event: dict[str, Any], ctx: ReactionContext) -> bool:  # pragma: no cover - interfejs
        """Zwraca True gdy reakcja została wykonana (zużywa limit)."""
        raise NotImplementedError
