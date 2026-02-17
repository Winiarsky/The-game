from GameObjects.Terrains.basic_terrain import BasicTerrain
from GameObjects.base import GameObjectMeta


class BushesTerrain(BasicTerrain):
    """Trudny teren – krzaki spowalniają ruch (dodatkowe 5 stóp za pole)."""

    name = "bushes"
    terrain_tags = ("bushes",)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.move_cost_bonus_feet = 5


META = GameObjectMeta(
    object_id="bushes_field",
    label="Bushes",
    color="#4b7b3f",
    category="Terrains",
    placement="cell",
    description="Krzaki – trudny teren, ruch kosztuje dodatkowe 5 stóp za pole.",
    logic_cls=BushesTerrain,
)
