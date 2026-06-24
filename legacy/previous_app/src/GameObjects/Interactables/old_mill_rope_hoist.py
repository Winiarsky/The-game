from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from old_mill_encounter import use_rope_hoist


class OldMillRopeHoist(InteractableMixin):
    def __init__(self, *, label: str = "Wciagarka workow") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "old_mill_rope_hoist"
        self.name = str(label or "Wciagarka workow")
        self.register_action(
            Interaction(
                id="drop_sacks",
                label="Zrzuc worki",
                description="Zablokuj przejscie albo spowolnij straznika na jedna runde.",
                handler=OldMillRopeHoist.action_drop,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakoncz", handler=lambda *_: "Koniec interakcji."))

    def action_drop(self, actor, game, _payload=None) -> str:
        return use_rope_hoist(game)


META = GameObjectMeta(
    object_id="old_mill_rope_hoist",
    label="Wciagarka workow",
    color="#fde047",
    category="Interactables",
    placement="cell",
    description="Jednorazowa taktyczna interakcja do kontroli ruchu.",
    logic_cls=OldMillRopeHoist,
    default_config={"label": "Wciagarka workow"},
)
