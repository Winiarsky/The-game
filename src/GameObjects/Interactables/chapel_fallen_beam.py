from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources


class ChapelFallenBeam(InteractableMixin):
    def __init__(self, *, beam_id: str = "fallen_beam", dc: int = 15) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.beam_id = str(beam_id or "fallen_beam")
        self.scenario_object_id = self.beam_id
        self.name = "Spalona belka"
        self.label = "Spalona belka"
        self.interaction_label = "Spalona belka"
        self.dc = int(dc or 15)
        self.register_default_actions()

    def register_default_actions(self) -> None:
        self.register_action(
            Interaction(
                id="move",
                label="Przesun belke",
                description=f"Atletyka DC {self.dc}; po sukcesie przestaw fizyczny znacznik belki.",
                handler=ChapelFallenBeam.action_move,
                end_interaction=False,
            )
        )
        self.register_action(
            Interaction(
                id="inspect",
                label="Obejrzyj belke",
                description="Sprawdz jak blokuje przejscie.",
                handler=ChapelFallenBeam.action_inspect,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakoncz", description="Zakoncz interakcje.", handler=lambda *_: "Koniec interakcji."))

    def action_inspect(self, actor, game, _payload=None) -> str:
        return "Spalona belka lezy na trasie miedzy posagami. Brazowe swiatlo wskazuje fizyczny znacznik do przesuniecia."

    def action_move(self, actor, game, _payload=None) -> str:
        from burned_chapel_encounter import apply_backlash, move_fallen_beam

        result = resolve_skill_check_with_sources(
            skill_id="athletics",
            dc=self.dc,
            actor=actor,
            target=self,
            tags=["athletics", "burned_chapel", "fallen_beam", "terrain"],
            game=game,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            return f"{move_fallen_beam(game)} (wynik: {outcome}, suma: {result.total})"
        penalty = apply_backlash(game, actor=actor, reason="fallen_beam_failure")
        return f"Belka trzeszczy, ale zostaje na miejscu. {penalty} (wynik: {outcome}, suma: {result.total})"


META = GameObjectMeta(
    object_id="chapel_fallen_beam",
    label="Spalona belka",
    color="#92400e",
    category="Interactables",
    placement="cell",
    description="Fizyczny znacznik belki w spalonej kaplicy; po sukcesie gracze przesuwaja go na planszy.",
    logic_cls=ChapelFallenBeam,
    default_config={"beam_id": "fallen_beam", "dc": 15},
)


__all__ = ["ChapelFallenBeam", "META"]
