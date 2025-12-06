from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Obstacle:
    """Bazowa klasa przeszkody zajmującej pole."""

    position: Optional[Tuple[int, int]] = None

    def set_position(self, position: Optional[Tuple[int, int]]) -> None:
        self.position = position

    def __repr__(self) -> str:  # podgląd w logach/debuggerze
        return f"Obstacle(position={self.position})"
