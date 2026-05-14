from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from hill_ruins_encounter import consume_hallowed_ash_vial, move_ash_storm, prompt_info
from skills import Skill


class HillRuinsAshStorm(InteractableMixin):
    def __init__(self, *, dc: int = 15) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.scenario_object_id = "hill_ruins_ash_storm"
        self.name = "Wir popiołu"
        self.dc = int(dc or 15)
        for skill in (Skill.OCCULTISM.value, Skill.NATURE.value, Skill.RELIGION.value):
            self.register_action(
                Interaction(
                    id=f"calm_{skill}",
                    label=f"Uspokój wir: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_calm(actor, game, skill_id),
                    end_interaction=False,
                )
            )
        self.register_action(
            Interaction(
                id="use_hallowed_ash",
                label="Użyj fiolki uświęconego popiołu",
                description="Zużywa consumable i ucisza wir na rundę.",
                handler=HillRuinsAshStorm.action_use_vial,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_calm(self, actor, game, skill_id: str) -> str:
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "hill_ruins", "ash_storm"],
            game=game,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            prompt_info(game, "Wir popiołu", "Wir traci siłę na tę rundę. Ranged i czary mają czystsze linie.", source="ash_storm_calmed")
            return f"Uspokajasz wir popiołu. (wynik: {outcome}, suma: {result.total})"
        pos = move_ash_storm(game)
        return f"Wir wyrywa się spod kontroli i przesuwa na {pos}. (wynik: {outcome}, suma: {result.total})"

    def action_use_vial(self, actor, game, _payload=None) -> str:
        consumed, msg = consume_hallowed_ash_vial(game, actor)
        if consumed:
            prompt_info(game, "Wir popiołu", msg, source="hallowed_ash_vial")
        return msg


META = GameObjectMeta(
    object_id="hill_ruins_ash_storm",
    label="Wir popiołu",
    color="#e5e7eb",
    category="Interactables",
    placement="cell",
    description="Ruchoma strefa popiołu utrudniająca walkę i rytuał.",
    logic_cls=HillRuinsAshStorm,
    default_config={"dc": 15},
)
