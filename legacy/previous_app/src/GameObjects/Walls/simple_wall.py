from GameObjects.Walls.basic_wall import BasicWall
from GameObjects.base import GameObjectMeta


class SimpleWall(BasicWall):
    """Podstawowa ściana między polami (w edytorze)."""


META = GameObjectMeta(
    object_id="simple_wall",
    label="Ściana",
    color="#555",
    category="Walls",
    placement="edge",
    description="Prosta ściana blokująca przejście.",
    logic_cls=SimpleWall,
)
