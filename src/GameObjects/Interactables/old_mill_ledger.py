from __future__ import annotations

from typing import Any

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from old_mill_encounter import increase_alarm, secure_ledger
from skills import Skill


class OldMillLedger(InteractableMixin):
    def __init__(self, *, dc: int = 15, label: str = "Księga młyna") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "old_mill_ledger"
        self.name = str(label or "Księga młyna")
        self.dc = int(dc or 15)
        for skill in (Skill.SOCIETY.value, Skill.THIEVERY.value):
            self.register_action(
                Interaction(
                    id=f"secure_{skill}",
                    label=f"Zabezpiecz stronę: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_secure(actor, game, skill_id),
                    end_interaction=False,
                    tags=[skill, "old_mill", "ledger"],
                )
            )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_secure(self, actor, game, skill_id: str) -> str:
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "old_mill", "ledger", "evidence"],
            game=game,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            return f"{secure_ledger(game)} (wynik: {outcome}, suma: {result.total})"
        if outcome == "critical_failure":
            increase_alarm(game, reason="Kartki rozsypują się na podłogę, a tylny strażnik odwraca głowę.")
        return f"Księga jest zaszyfrowana skrótami płatności; jeszcze nie macie pewnego dowodu. (wynik: {outcome}, suma: {result.total})"


META = GameObjectMeta(
    object_id="old_mill_ledger",
    label="Księga młyna",
    color="#a16207",
    category="Interactables",
    placement="cell",
    description="Dowód płatności i transportu fałszywego popiołu.",
    logic_cls=OldMillLedger,
    default_config={"dc": 15, "label": "Księga młyna"},
)
