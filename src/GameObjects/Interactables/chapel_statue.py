from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin


class ChapelStatue(InteractableMixin):
    def __init__(self, *, statue_id: str = "watcher", label: str = "Posag kaplicy") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.statue_id = str(statue_id or "watcher").strip().lower()
        self.scenario_object_id = f"chapel_statue_{self.statue_id}"
        self.name = str(label or self.statue_id)
        self.label = self.name
        self.interaction_label = self.name
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(Interaction(id="activate", label="Aktywuj posag", description="Po przebudzeniu oltarza sprawdza kolejny krok sekwencji.", handler=ChapelStatue.action_activate, end_interaction=False))
        self.register_action(Interaction(id="inspect", label="Obejrzyj posag", description="Opis sceny.", handler=ChapelStatue.action_inspect, end_interaction=False))
        self.register_action(Interaction(id="leave", label="Zakoncz", description="Zakoncz interakcje.", handler=lambda *_: "Koniec interakcji."))

    def action_inspect(self, actor, game, _payload=None) -> str:
        descriptions = {
            "watcher": "Posag osoby, ktora patrzyla na przygotowania do rytualu.",
            "bellbearer": "Posag z lina dzwonu, ktory nigdy nie zabrzmial.",
            "flamekeeper": "Posag dloni niosacej pierwszy rytualny plomien.",
            "ash_saint": "Posag kleczacej postaci zasypanej popiolem.",
        }
        return descriptions.get(self.statue_id, "Zweglony posag z zatarta scena.")

    def action_activate(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import activate_statue

        return activate_statue(game, self.statue_id, actor=actor)


META = GameObjectMeta(
    object_id="chapel_statue",
    label="Posag kaplicy",
    color="#f59e0b",
    category="Interactables",
    placement="cell",
    description="Fizyczny posag-sekwencja w spalonej kaplicy.",
    logic_cls=ChapelStatue,
    default_config={"statue_id": "watcher", "label": "Posag kaplicy"},
)


__all__ = ["ChapelStatue", "META"]
