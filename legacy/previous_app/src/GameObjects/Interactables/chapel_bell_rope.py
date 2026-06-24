from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin


class ChapelBellRope(InteractableMixin):
    def __init__(self, *, rope_id: str = "chapel_bell_rope") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.rope_id = str(rope_id or "chapel_bell_rope")
        self.scenario_object_id = self.rope_id
        self.name = "Hanging Bell Rope"
        self.label = "Hanging Bell Rope"
        self.interaction_label = "Hanging Bell Rope"
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(Interaction(id="ring", label="Pociagnij line dzwonu", description="Rozprasza popielne miniony na jedna runde.", handler=ChapelBellRope.action_ring, end_interaction=False))
        self.register_action(Interaction(id="leave", label="Zakoncz", description="Zakoncz interakcje.", handler=lambda *_: "Koniec interakcji."))

    def action_ring(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import active_cinders, combat_round, ensure_state, prompt_info

        ensure_state(game)["bell_rung_round"] = combat_round(game)
        for cinder in active_cinders(game):
            try:
                cinder.ai_memory["slowed_by_bell_round"] = combat_round(game)
                cinder.distance = min(int(getattr(cinder, "distance", 25) or 25), 10)
            except Exception:
                pass
        msg = "Pekniety dzwon odpowiada suchym tonem. Popielne cienie traca tempo na te runde."
        prompt_info(game, "Bell Rope", msg, source="bell_rope")
        return msg


META = GameObjectMeta(
    object_id="chapel_bell_rope",
    label="Hanging Bell Rope",
    color="#f8fafc",
    category="Interactables",
    placement="cell",
    description="Taktyczna interakcja w spalonej kaplicy; na krotko spowalnia popielne miniony.",
    logic_cls=ChapelBellRope,
    default_config={"rope_id": "chapel_bell_rope"},
)


__all__ = ["ChapelBellRope", "META"]
