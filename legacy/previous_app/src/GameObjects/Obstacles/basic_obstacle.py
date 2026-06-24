from dataclasses import dataclass, field
from typing import Optional, Tuple

from GameObjects.interactions_mixin import RangeAttackAffectMixin
from object_registry import assign_id


@dataclass
class Obstacle(RangeAttackAffectMixin):
    """Bazowa klasa przeszkody zajmującej pole."""

    object_id: str = field(init=False)
    position: Optional[Tuple[int, int]] = None
    stealth_impact: int = 0
    cover_type: str = "greater"

    def __post_init__(self):
        self.object_id = assign_id(self)

    def set_position(self, position: Optional[Tuple[int, int]]) -> None:
        self.position = position

    def on_critical_stealth_fail(self):
        return None

    def __repr__(self) -> str:  # podgląd w logach/debuggerze
        return f"Obstacle(position={self.position})"
