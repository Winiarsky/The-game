from GameObjects.base import GameObjectMeta
from GameObjects.Terrains.basic_terrain import BasicTerrain


class BlockedField(BasicTerrain):
    """Teren nieprzechodni."""

    def __init__(self) -> None:
        super().__init__(name="blocked", walkable=False)


# Podstawowy teren nieprzechodni (mapowany na blocked_fields w scenariuszu i obiektach).
META = GameObjectMeta(
    object_id="blocked_field",
    label="Pole zablokowane",
    color="#c44",
    category="Terrains",
    placement="cell",
    description="Pole nieprzechodne.",
    logic_cls=BlockedField,
)
