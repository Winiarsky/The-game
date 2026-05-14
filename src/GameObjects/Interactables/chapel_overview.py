from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin


class ChapelOverview(InteractableMixin):
    def __init__(self, *, overview_id: str = "chapel_overview") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.overview_id = str(overview_id or "chapel_overview")
        self.scenario_object_id = self.overview_id
        self.name = "Rozejrzyj się po kaplicy"
        self.label = "Rozejrzyj się po kaplicy"
        self.interaction_label = "Rozejrzyj się po kaplicy"
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(
            Interaction(
                id="inspect",
                label="Rozejrzyj się po kaplicy",
                description="Pokaż najważniejsze punkty mapy i ich LED-y.",
                handler=ChapelOverview.action_inspect,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", description="Zakończ interakcję.", handler=lambda *_: "Koniec interakcji."))

    def action_inspect(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import present_chapel_overview

        return present_chapel_overview(game)


META = GameObjectMeta(
    object_id="chapel_overview",
    label="Rozejrzyj się po kaplicy",
    color="#facc15",
    category="Interactables",
    placement="cell",
    description="Wejściowy briefing Spalonej Kaplicy: wskazuje ołtarz, konfesjonał, posągi, belkę, pułapki i cel mapy.",
    logic_cls=ChapelOverview,
    default_config={"overview_id": "chapel_overview"},
)


__all__ = ["ChapelOverview", "META"]
