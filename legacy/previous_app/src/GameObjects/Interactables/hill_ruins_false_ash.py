from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from hill_ruins_encounter import expose_false_ash, flag_enabled, backlash
from skills import Skill


class HillRuinsFalseAsh(InteractableMixin):
    def __init__(self, *, dc: int = 14) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "hill_ruins_false_ash_drift"
        self.name = "Fałszywy popiół na wietrze"
        self.dc = int(dc or 14)
        self.register_action(
            Interaction(
                id="compare_sample",
                label="Porównaj próbkę",
                description="Użyj próbki z młyna, jeśli została zabezpieczona.",
                handler=HillRuinsFalseAsh.action_compare,
                end_interaction=False,
            )
        )
        for skill in (Skill.SURVIVAL.value, Skill.CRAFTING.value, Skill.OCCULTISM.value):
            self.register_action(
                Interaction(
                    id=f"inspect_{skill}",
                    label=f"Zbadaj popiół: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_inspect(actor, game, skill_id),
                    end_interaction=False,
                )
            )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_compare(self, actor, game, _payload=None) -> str:
        if not flag_enabled(game, "false_ash_secured"):
            return "Nie macie zabezpieczonej próbki fałszywego popiołu z młyna."
        return expose_false_ash(game)

    def action_inspect(self, actor, game, skill_id: str) -> str:
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "hill_ruins", "false_ash"],
            game=game,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            return f"{expose_false_ash(game)} (wynik: {outcome}, suma: {result.total})"
        penalty = backlash(game, reason="false_ash")
        return f"Popiół miesza ślady i wspomnienie traci ostrość. {penalty} (wynik: {outcome}, suma: {result.total})"


META = GameObjectMeta(
    object_id="hill_ruins_false_ash",
    label="Fałszywy popiół",
    color="#9ca3af",
    category="Interactables",
    placement="cell",
    description="Punkt porównania fałszywego popiołu z młyna ze śladem ruin.",
    logic_cls=HillRuinsFalseAsh,
    default_config={"dc": 14},
)
