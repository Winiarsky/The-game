from GameObjects.base import GameObjectMeta
from GameObjects.Obstacles.basic_obstacle import Obstacle


class SimpleObstacle(Obstacle):
    """Podstawowa przeszkoda zajmująca pole."""


META = GameObjectMeta(
    object_id="simple_obstacle",
    label="Przeszkoda",
    color="#333",
    category="Obstacles",
    placement="cell",
    description="Podstawowa przeszkoda blokująca pole.",
    logic_cls=SimpleObstacle,
)
