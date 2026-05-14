from __future__ import annotations

from GameObjects.base import GameObjectMeta
from GameObjects.interactions_mixin.base_interaction import Interaction, InteractableMixin
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from oath_crypt_encounter import (
    PROOF_PILLAR_LABELS,
    present_proof,
    proof_bonus,
    reject_proof,
)
from skills import Skill


SKILLS_BY_PROOF = {
    "oath": (Skill.RELIGION.value, Skill.SOCIETY.value, Skill.OCCULTISM.value),
    "ash": (Skill.SURVIVAL.value, Skill.CRAFTING.value, Skill.OCCULTISM.value),
    "ledger": (Skill.SOCIETY.value, Skill.THIEVERY.value, Skill.DIPLOMACY.value),
    "witness": (Skill.DIPLOMACY.value, Skill.RELIGION.value, Skill.SOCIETY.value),
}


class OathCryptProofPillar(InteractableMixin):
    def __init__(self, *, proof_id: str = "oath", dc: int = 16) -> None:
        super().__init__(position=None, allow_same_cell_interact=True, blocks_movement=False)
        self.proof_id = str(proof_id or "oath").strip()
        self.scenario_object_id = f"oath_crypt_proof_{self.proof_id}"
        self.dc = int(dc or 16)
        self.name = PROOF_PILLAR_LABELS.get(self.proof_id, "Filar dowodu")
        for skill in SKILLS_BY_PROOF.get(self.proof_id, (Skill.SOCIETY.value,)):
            self.register_action(
                Interaction(
                    id=f"present_{skill}",
                    label=f"Przedstaw dowód: {skill.title()}",
                    description=f"{skill.title()} DC {self.dc}.",
                    handler=lambda obj, actor, game, payload, skill_id=skill: obj.action_present(actor, game, skill_id),
                    end_interaction=False,
                    tags=[skill, "oath_crypt", "proof"],
                )
            )
        self.register_action(
            Interaction(
                id="use_evidence",
                label="Użyj zebranego dowodu",
                description="Wykorzystaj pasujący dowód z poprzednich map.",
                handler=OathCryptProofPillar.action_use_evidence,
                end_interaction=False,
            )
        )
        self.register_action(Interaction(id="leave", label="Zakończ", handler=lambda *_: "Koniec interakcji."))

    def action_present(self, actor, game, skill_id: str) -> str:
        bonus = proof_bonus(game, self.proof_id)
        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=self.dc,
            actor=actor,
            target=self,
            tags=[skill_id, "oath_crypt", "proof", self.proof_id],
            game=game,
            base_modifier=bonus,
            apply_modifiers=True,
        )
        outcome = str(result.outcome or "")
        if outcome in {"success", "critical_success"}:
            _ok, msg = present_proof(game, self.proof_id, method=skill_id)
            note = f" Premia z wcześniejszych dowodów: {bonus:+d}." if bonus else ""
            return f"{msg}{note} (wynik: {outcome}, suma: {result.total})"
        penalty = reject_proof(game, reason=f"{self.proof_id}:{skill_id}")
        return f"{self.name} odrzuca argument. {penalty} (wynik: {outcome}, suma: {result.total})"

    def action_use_evidence(self, actor, game, _payload=None) -> str:
        if proof_bonus(game, self.proof_id) <= 0:
            return "Nie macie jeszcze dowodu, który pasuje do tego filaru."
        _ok, msg = present_proof(game, self.proof_id, method="evidence")
        return f"Dowód z wcześniejszej mapy rezonuje z kryptą. {msg}"


META = GameObjectMeta(
    object_id="oath_crypt_proof_pillar",
    label="Filar dowodu",
    color="#eab308",
    category="Interactables",
    placement="cell",
    description="Filar finałowego sądu przysięgi przyjmujący jeden typ dowodu.",
    logic_cls=OathCryptProofPillar,
    default_config={"proof_id": "oath", "dc": 16},
)
