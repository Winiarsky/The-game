from GameObjects.Terrains.basic_terrain import BasicTerrain
from GameObjects.base import GameObjectMeta


class RumbleTerrain(BasicTerrain):
    """Trudny teren – spowalnia ruch (dodatkowe 5 stóp za pole)."""

    name = "rumble"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.move_cost_bonus_feet = 5


META = GameObjectMeta(
    object_id="rumble_field",
    label="Rumble",
    color="#8d6e63",
    category="Terrains",
    placement="cell",
    description="Trudny teren – ruch kosztuje dodatkowe 5 stóp za pole.",
    logic_cls=RumbleTerrain,
)
