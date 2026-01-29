from GameObjects.Terrains.basic_terrain import BasicTerrain
from GameObjects.base import GameObjectMeta


class SimpleTerrain(BasicTerrain):
    """Zwykłe, przechodnie pole planszy."""


META = GameObjectMeta(
    object_id="plain_field",
    label="Zwykłe pole",
    color="#7cb342",
    category="Terrains",
    placement="cell",
    description="Podstawowy, przechodni teren.",
    logic_cls=SimpleTerrain,
)
