from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.combat import SceneFlags, scene_flag
from dnd_board_game.rules import RollMode

from .models import NpcArgumentEvaluationPolicy


@dataclass(frozen=True, slots=True)
class NpcArgumentLeverageClaim:
    id: str
    strength: int


@dataclass(frozen=True, slots=True)
class NpcArgumentAssessment:
    intent_fit: int
    specificity: int
    credibility: int
    leverage_claims: tuple[NpcArgumentLeverageClaim, ...] = ()


@dataclass(frozen=True, slots=True)
class NpcArgumentAdjustment:
    score: int
    modifier: int = 0
    roll_mode: RollMode = RollMode.NORMAL
    accepted_leverage_ids: tuple[str, ...] = ()


def evaluate_npc_argument(
    policy: NpcArgumentEvaluationPolicy,
    assessment: NpcArgumentAssessment,
    *,
    selected_skill: str,
    flags: SceneFlags,
) -> NpcArgumentAdjustment:
    """Validate an LLM assessment against authored facts and map it to a roll adjustment."""
    if assessment.intent_fit not in {-2, 0, 1}:
        raise ValueError("Argument intent_fit must be one of -2, 0, 1.")
    if assessment.specificity not in {0, 1}:
        raise ValueError("Argument specificity must be 0 or 1.")
    if assessment.credibility not in {-2, -1, 0}:
        raise ValueError("Argument credibility must be one of -2, -1, 0.")
    skill = selected_skill.strip().lower()
    if skill not in {"persuasion", "deception", "intimidation"}:
        raise ValueError("Argument evaluation requires a social skill.")
    claims_by_id: dict[str, int] = {}
    for claim in assessment.leverage_claims:
        claim_id = claim.id.strip().lower()
        if not claim_id or claim_id in claims_by_id:
            raise ValueError("Argument leverage claims require unique non-empty ids.")
        claims_by_id[claim_id] = claim.strength
    authored = {item.id: item for item in policy.leverages}
    leverage_score = 0
    accepted: list[str] = []
    for claim_id, strength in claims_by_id.items():
        leverage = authored.get(claim_id)
        if leverage is None:
            continue
        if leverage.compatible_skills and skill not in leverage.compatible_skills:
            continue
        if not all(scene_flag(flags, flag, False) for flag in leverage.required_flags):
            continue
        if strength < 1:
            continue
        leverage_score += min(strength, leverage.max_strength)
        accepted.append(claim_id)
    score = (
        assessment.intent_fit
        + assessment.specificity
        + assessment.credibility
        + leverage_score
        + sum(
            modifier
            for flag, modifier in policy.flag_modifiers
            if bool(scene_flag(flags, flag, False))
        )
    )
    if score >= 4:
        return NpcArgumentAdjustment(score, roll_mode=RollMode.ADVANTAGE, accepted_leverage_ids=tuple(accepted))
    if score <= -3:
        return NpcArgumentAdjustment(score, roll_mode=RollMode.DISADVANTAGE, accepted_leverage_ids=tuple(accepted))
    modifier = 2 if score == 3 else 1 if score in {1, 2} else -1 if score == -1 else -2 if score == -2 else 0
    return NpcArgumentAdjustment(score, modifier=modifier, accepted_leverage_ids=tuple(accepted))


__all__ = [
    "NpcArgumentAdjustment",
    "NpcArgumentAssessment",
    "NpcArgumentLeverageClaim",
    "evaluate_npc_argument",
]
