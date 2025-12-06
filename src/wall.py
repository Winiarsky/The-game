from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple


@dataclass(slots=True)
class Wall:
    """Ściana blokująca przejście między dwoma polami."""

    a: Tuple[int, int]
    b: Tuple[int, int]
    hardness: Optional[int] = None
    features: Dict[str, Any] = field(default_factory=dict)

    @property
    def key(self) -> frozenset[Tuple[int, int]]:
        return frozenset((self.a, self.b))

    def __repr__(self) -> str:
        return f"Wall(a={self.a}, b={self.b}, hardness={self.hardness}, features={self.features})"
