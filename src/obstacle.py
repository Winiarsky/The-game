from dataclasses import dataclass, field
from typing import Optional, Tuple

from object_registry import assign_id


@dataclass
class Obstacle:
    """Bazowa klasa przeszkody zajmującej pole."""

    object_id: str = field(init=False)
    position: Optional[Tuple[int, int]] = None
    stealth_impact: int = 0

    def __post_init__(self):
        self.object_id = assign_id(self)

    def set_position(self, position: Optional[Tuple[int, int]]) -> None:
        self.position = position

    def on_critical_stealth_fail(self):
        return None

    def __repr__(self) -> str:  # podgląd w logach/debuggerze
        return f"Obstacle(position={self.position})"
