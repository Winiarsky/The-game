from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from hill_ruins_encounter import add_ritual_stability, backlash, flag_enabled, set_flag
from skills import Skill


class HillRuinsEcho(InteractableMixin):
    def __init__(self, *, dc: int = 15) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "hill_ruins_oath_echo"
        self.name = "Echo Przysięgi"
        self.dc = int(dc or 15)
        for skill in (Skill.RELIGION.value, Skill.SOCIETY.value, Skill.DIPLOMACY.value):
            self.register_action(
                Interaction(
                    id=f"invoke_{skill}",
                    label=f"Przywołaj echo: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_invoke(actor, game, skill_id),
                    end_interaction=False,
                )
            )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_invoke(self, actor, game, skill_id: str) -> str:
        bonus = 2 if any(flag_enabled(game, flag) for flag in ("warden_medallion_recovered", "mill_ledger_secured", "tovin_rescued")) else 0
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "hill_ruins", "oath_echo"],
            game=game,
            base_modifier=bonus,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            set_flag(game, "mira_memory_stabilized")
            _ok, msg = add_ritual_stability(game, anchor_id=None, method="oath_echo")
            return f"Echo potwierdza, że Mira utrzymuje pamięć przysięgi, nie klątwę. {msg} (wynik: {outcome}, suma: {result.total})"
        penalty = backlash(game, reason="oath_echo")
        return f"Echo pęka na sprzecznych zeznaniach. {penalty} (wynik: {outcome}, suma: {result.total})"


META = GameObjectMeta(
    object_id="hill_ruins_echo",
    label="Echo Przysięgi",
    color="#facc15",
    category="Interactables",
    placement="cell",
    description="Punkt dowodów i przysięgi wspierający rytuał Miry.",
    logic_cls=HillRuinsEcho,
    default_config={"dc": 15},
)
