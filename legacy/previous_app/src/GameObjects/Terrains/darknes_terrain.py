from GameObjects.base import GameObjectMeta
from GameObjects.Terrains.basic_terrain import BasicTerrain
from statuses import BLINDED_STATUS, CONCEALED_STATUS, IN_DARK_STATUS


class DarknesTerrain(BasicTerrain):
    """Teren ciemności – nadaje status InDark."""

    name = "darkness"
    terrain_tags = ("darkness",)

    def on_enter(self, actor, _game):
        if actor is None:
            return None
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            adder(BLINDED_STATUS)
            adder(CONCEALED_STATUS)
            adder(IN_DARK_STATUS)
            return None
        statuses = getattr(actor, "statuses", None)
        if isinstance(statuses, list):
            if BLINDED_STATUS not in statuses:
                statuses.append(BLINDED_STATUS)
            if CONCEALED_STATUS not in statuses:
                statuses.append(CONCEALED_STATUS)
            if IN_DARK_STATUS not in statuses:
                statuses.append(IN_DARK_STATUS)
        return None


META = GameObjectMeta(
    object_id="darkness_field",
    label="Darkness",
    color="#212121",
    category="Terrains",
    placement="cell",
    description="Ciemny teren – daje status In Dark.",
    logic_cls=DarknesTerrain,
)
