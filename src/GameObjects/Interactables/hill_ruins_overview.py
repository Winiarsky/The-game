from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from hill_ruins_encounter import present_overview


class HillRuinsOverview(InteractableMixin):
    def __init__(self, *, overview_id: str = "hill_ruins_overview") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.overview_id = str(overview_id or "hill_ruins_overview")
        self.scenario_object_id = self.overview_id
        self.name = "Rozejrzyj się po ruinach"
        self.register_action(
            Interaction(
                id="overview",
                label="Rozejrzyj się",
                description="Pokaż kluczowe punkty rytuału i LED-y.",
                handler=HillRuinsOverview.action_overview,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_overview(self, actor, game, _payload=None) -> str:
        return present_overview(game)


META = GameObjectMeta(
    object_id="hill_ruins_overview",
    label="Opis ruin na wzgórzu",
    color="#93c5fd",
    category="Interactables",
    placement="cell",
    description="Wejściowy opis mapy rytuału w ruinach.",
    logic_cls=HillRuinsOverview,
    default_config={"overview_id": "hill_ruins_overview"},
)
