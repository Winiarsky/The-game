from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Status:
    """Pojedynczy status postaci/obiektu."""

    id: str
    label: Optional[str] = None
    duration: Optional[int] = None
    source: Optional[str] = None
    stacks: bool = False
    data: dict[str, Any] = field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Status):
            return self.id == other.id
        if isinstance(other, str):
            return self.id == other
        return False

    def __hash__(self) -> int:  # pragma: no cover - dataclass + eq already predictable
        return hash(self.id)

    @property
    def display_label(self) -> str:
        """Etykieta pokazywana w UI/logach."""
        return self.label or self.id
