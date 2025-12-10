from GameObjects.base import GameObjectMeta
from wall import Wall


class BasicWall(Wall):
    """Ściana między dwoma polami."""


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
