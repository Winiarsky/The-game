from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from oath_crypt_encounter import present_overview


class OathCryptOverview(InteractableMixin):
    def __init__(self, *, overview_id: str = "oath_crypt_overview") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.overview_id = str(overview_id or "oath_crypt_overview")
        self.scenario_object_id = self.overview_id
        self.name = "Krypta Przysięgi"
        self.register_action(
            Interaction(
                id="inspect",
                label="Oceń kryptę",
                description="Pokazuje cel mapy, filary dowodów i stan LED-ów.",
                handler=lambda obj, actor, game, payload: present_overview(game),
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))


META = GameObjectMeta(
    object_id="oath_crypt_overview",
    label="Krypta Przysięgi",
    color="#cbd5e1",
    category="Interactables",
    placement="cell",
    description="Wejściowy opis finałowej mapy i jej fizycznych punktów.",
    logic_cls=OathCryptOverview,
    default_config={"overview_id": "oath_crypt_overview"},
)
