from __future__ import annotations

from typing import Any

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from old_mill_encounter import flag_enabled, increase_alarm, secure_false_ash
from skills import Skill


class OldMillSacks(InteractableMixin):
    def __init__(self, *, dc: int = 14, label: str = "Worki maki i falszywego popiolu") -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "old_mill_false_ash_sacks"
        self.name = str(label or "Worki maki i falszywego popiolu")
        self.dc = int(dc or 14)
        for skill in (Skill.SURVIVAL.value, Skill.CRAFTING.value, Skill.OCCULTISM.value):
            self.register_action(
                Interaction(
                    id=f"inspect_{skill}",
                    label=f"Zabezpiecz probke: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_secure(actor, game, skill_id),
                    end_interaction=False,
                    tags=[skill, "old_mill", "evidence"],
                )
            )
        self.register_action(Interaction(id="leave", label="Zakoncz", handler=lambda *_: "Koniec interakcji."))

    def action_secure(self, actor, game, skill_id: str) -> str:
        bonus = 2 if flag_enabled(game, "villager_mill_hint") or flag_enabled(game, "chapel_tracks_read") else 0
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "old_mill", "false_ash", "evidence"],
            game=game,
            base_modifier=bonus,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            return f"{secure_false_ash(game)} (wynik: {outcome}, suma: {result.total})"
        if outcome == "critical_failure":
            increase_alarm(game, reason="Worek peknie i szary pyl idzie w powietrze. Straznicy wiedza, czego szukacie.")
        return f"Probka rozsypuje sie i trudno odroznic pyl od zwyklej maki. (wynik: {outcome}, suma: {result.total})"


META = GameObjectMeta(
    object_id="old_mill_sacks",
    label="Worki falszywego popiolu",
    color="#d1d5db",
    category="Interactables",
    placement="cell",
    description="Dowod falszywego popiolu do zabezpieczenia.",
    logic_cls=OldMillSacks,
    default_config={"dc": 14, "label": "Worki maki i falszywego popiolu"},
)
