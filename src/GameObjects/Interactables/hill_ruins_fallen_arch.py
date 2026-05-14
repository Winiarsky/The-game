from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from hill_ruins_encounter import backlash, support_fallen_arch
from skills import Skill


class HillRuinsFallenArch(InteractableMixin):
    def __init__(self, *, dc: int = 15) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "hill_ruins_fallen_arch"
        self.name = "Zawalony łuk"
        self.dc = int(dc or 15)
        for skill in (Skill.ATHLETICS.value, Skill.CRAFTING.value):
            self.register_action(
                Interaction(
                    id=f"support_{skill}",
                    label=f"Podeprzyj łuk: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_support(actor, game, skill_id),
                    end_interaction=False,
                )
            )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_support(self, actor, game, skill_id: str) -> str:
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "hill_ruins", "fallen_arch"],
            game=game,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            return f"{support_fallen_arch(game)} (wynik: {outcome}, suma: {result.total})"
        penalty = backlash(game, reason="fallen_arch")
        return f"Łuk osuwa się i sypie popiołem na krąg. {penalty} (wynik: {outcome}, suma: {result.total})"


META = GameObjectMeta(
    object_id="hill_ruins_fallen_arch",
    label="Zawalony łuk",
    color="#a16207",
    category="Interactables",
    placement="cell",
    description="Interaktywny teren otwierający krótszą drogę albo tworzący presję rytuału.",
    logic_cls=HillRuinsFallenArch,
    default_config={"dc": 15},
)
