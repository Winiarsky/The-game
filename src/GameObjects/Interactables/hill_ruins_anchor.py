from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from hill_ruins_encounter import (
    ANCHOR_LABELS,
    add_ritual_stability,
    anchor_bonus,
    backlash,
    can_gain_stability_this_round,
    round_gate_message,
)
from skills import Skill


class HillRuinsAnchor(InteractableMixin):
    def __init__(self, *, anchor_id: str = "oath", dc: int = 15) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.anchor_id = str(anchor_id or "oath").strip()
        self.scenario_object_id = f"hill_ruins_anchor_{self.anchor_id}"
        self.dc = int(dc or 15)
        self.name = ANCHOR_LABELS.get(self.anchor_id, "Anchor rytuału")
        for skill in (Skill.OCCULTISM.value, Skill.RELIGION.value, Skill.SOCIETY.value):
            self.register_action(
                Interaction(
                    id=f"stabilize_{skill}",
                    label=f"Stabilizuj: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_stabilize(actor, game, skill_id),
                    end_interaction=False,
                    tags=[skill, "hill_ruins", "ritual_anchor"],
                )
            )
        self.register_action(
            Interaction(
                id="use_evidence",
                label="Użyj dowodu",
                description="Wykorzystaj dowód z wcześniejszej mapy jako przewagę rytuału.",
                handler=HillRuinsAnchor.action_use_evidence,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_stabilize(self, actor, game, skill_id: str) -> str:
        if not can_gain_stability_this_round(game):
            return round_gate_message(game)
        bonus = anchor_bonus(game, self.anchor_id)
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "hill_ruins", "ritual_anchor", self.anchor_id],
            game=game,
            base_modifier=bonus,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            _ok, msg = add_ritual_stability(game, anchor_id=self.anchor_id, method=skill_id)
            note = f" Premia z dowodów: {bonus:+d}." if bonus else ""
            return f"{msg}{note} (wynik: {outcome}, suma: {result.total})"
        penalty = backlash(game, reason=f"{self.anchor_id}:{skill_id}")
        return f"Anchor odrzuca rytuał. {penalty} (wynik: {outcome}, suma: {result.total})"

    def action_use_evidence(self, actor, game, _payload=None) -> str:
        if anchor_bonus(game, self.anchor_id) <= 0:
            return "Nie macie dowodu, który pasuje do tego anchora."
        if not can_gain_stability_this_round(game):
            return round_gate_message(game)
        _ok, msg = add_ritual_stability(game, anchor_id=self.anchor_id, method="evidence")
        return f"Dowód rezonuje z anchorem. {msg}"


META = GameObjectMeta(
    object_id="hill_ruins_anchor",
    label="Anchor rytuału",
    color="#60a5fa",
    category="Interactables",
    placement="cell",
    description="Obelisk rytuału Miry stabilizujący popielne wspomnienie.",
    logic_cls=HillRuinsAnchor,
    default_config={"anchor_id": "oath", "dc": 15},
)
