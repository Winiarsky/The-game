from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from old_mill_encounter import present_overview


class OldMillOverview(InteractableMixin):
    def __init__(self, *, label: str = "Rozejrzyj sie po mlynie") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "old_mill_overview"
        self.name = str(label or "Rozejrzyj sie po mlynie")
        self.register_action(
            Interaction(
                id="overview",
                label="Rozejrzyj sie",
                description="Pokaz kluczowe punkty mlyna i ich LED-y.",
                handler=OldMillOverview.action_overview,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakoncz", handler=lambda *_: "Koniec interakcji."))

    def action_overview(self, actor, game, _payload=None) -> str:
        return present_overview(game)


META = GameObjectMeta(
    object_id="old_mill_overview",
    label="Opis Starego Młyna",
    color="#facc15",
    category="Interactables",
    placement="cell",
    description="Wejsciowy opis taktyczno-sledczy Starego Mlyna.",
    logic_cls=OldMillOverview,
    default_config={"label": "Rozejrzyj sie po mlynie"},
)
