from GameObjects.base import GameObjectMeta
from GameObjects.Terrains.basic_terrain import BasicTerrain
from statuses import CONCEALED_STATUS, IN_DIM_LIGHT_STATUS


class DimLightTerrain(BasicTerrain):
    """Teren półmroku – daje status InDimLight stojącym na nim."""

    name = "dim_light"
    terrain_tags = ("dim_light",)

    def on_enter(self, actor, _game):
        if actor is None:
            return None
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            adder(CONCEALED_STATUS)
            adder(IN_DIM_LIGHT_STATUS)
            return None
        statuses = getattr(actor, "statuses", None)
        if isinstance(statuses, list):
            if CONCEALED_STATUS not in statuses:
                statuses.append(CONCEALED_STATUS)
            if IN_DIM_LIGHT_STATUS not in statuses:
                statuses.append(IN_DIM_LIGHT_STATUS)
        return None


META = GameObjectMeta(
    object_id="dim_light_field",
    label="Dim Light",
    color="#5c6bc0",
    category="Terrains",
    placement="cell",
    description="Półmrok – +2 do Stealth i ignoruje obserwację.",
    logic_cls=DimLightTerrain,
)
