from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin import RangeAttackAffectMixin
from object_registry import assign_id


@dataclass(slots=True)
class Wall(RangeAttackAffectMixin):
    """Ściana blokująca przejście między dwoma polami."""

    object_id: str = field(init=False)
    a: Tuple[int, int]
    b: Tuple[int, int]
    hardness: Optional[int] = None
    features: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.object_id = assign_id(self)

    @property
    def key(self) -> frozenset[Tuple[int, int]]:
        return frozenset((self.a, self.b))

    def __repr__(self) -> str:
        return f"Wall(a={self.a}, b={self.b}, hardness={self.hardness}, features={self.features})"


class Mur(Wall):
    """Przykładowy typ ściany z predefiniowaną twardością."""

    def __init__(
        self,
        a: tuple[int, int],
        b: tuple[int, int],
        *,
        hardness: int | None = None,
        features: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(a=a, b=b, hardness=hardness if hardness is not None else 100, features=features or {})


class BasicWall(Wall):
    """Ściana między dwoma polami."""
    cover_type = "block"


# Ściana między dwoma polami (mapowana na walls w scenariuszu).
META = GameObjectMeta(
    object_id="basic_wall",
    label="Ściana",
    color="#555",
    category="Walls",
    placement="edge",
    description="Podstawowa ściana między polami.",
    logic_cls=BasicWall,
)
