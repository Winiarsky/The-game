from GameObjects.Terrains.basic_terrain import BasicTerrain
from GameObjects.interactions_mixin import RangeAttackAffectMixin
from GameObjects.base import GameObjectMeta


class ForestTerrain(BasicTerrain, RangeAttackAffectMixin):
    """Pole leśne – standardowa osłona, tag forest, nie spowalnia ruchu."""

    name = "forest"
    cover_type = "standard"
    terrain_tags = ("forest",)


META = GameObjectMeta(
    object_id="forest_field",
    label="Forest",
    color="#2f7d32",
    category="Terrains",
    placement="cell",
    description="Leśny teren zapewniający naturalną osłonę.",
    logic_cls=ForestTerrain,
)
