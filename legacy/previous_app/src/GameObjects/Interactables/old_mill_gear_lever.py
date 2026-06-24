from __future__ import annotations

from typing import Any

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from old_mill_encounter import disable_mechanism, increase_alarm
from skills import Skill


class OldMillGearLever(InteractableMixin):
    def __init__(self, *, dc: int = 15, label: str = "Dzwignia mechanizmu mlyna") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "old_mill_gear_lever"
        self.name = str(label or "Dzwignia mechanizmu mlyna")
        self.dc = int(dc or 15)
        for skill in (Skill.THIEVERY.value, Skill.CRAFTING.value):
            self.register_action(
                Interaction(
                    id=f"disable_{skill}",
                    label=f"Unieruchom: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}. Porażka podnosi alarm.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_disable(actor, game, skill_id),
                    end_interaction=False,
                    tags=[skill, "old_mill", "mechanism"],
                )
            )
        self.register_action(Interaction(id="leave", label="Zakoncz", handler=lambda *_: "Koniec interakcji."))

    def action_disable(self, actor, game, skill_id: str) -> str:
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "old_mill", "mechanism", "disable"],
            game=game,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            return f"{disable_mechanism(game)} (wynik: {outcome}, suma: {result.total})"
        increase_alarm(game, reason="Mechanizm zgrzyta glosno, gdy dzwignia wraca na miejsce.")
        return f"Nie udaje sie unieruchomic mechanizmu. Alarm rosnie. (wynik: {outcome}, suma: {result.total})"


META = GameObjectMeta(
    object_id="old_mill_gear_lever",
    label="Dzwignia mlyna",
    color="#fbbf24",
    category="Interactables",
    placement="cell",
    description="Test Thievery/Crafting do wylaczenia pulapki mechanizmu.",
    logic_cls=OldMillGearLever,
    default_config={"dc": 15, "label": "Dzwignia mechanizmu mlyna"},
)
