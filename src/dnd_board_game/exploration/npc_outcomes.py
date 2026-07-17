from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.combat import scene_flag

from .effects import ExplorationEffectResult, apply_exploration_effect
from .models import (
    ExplorationState,
    NpcIntentPermission,
    NpcIntentTarget,
    NpcOutcomeBranch,
    NpcOutcomeTier,
)


@dataclass(frozen=True, slots=True)
class NpcIntentActionPlan:
    intent: str
    target: NpcIntentTarget
    quantity: int

    def as_payload(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "target_id": self.target.id,
            "target_label": self.target.label,
            "description": self.target.description,
            "reward_label": self.target.reward_label,
            "risk_summary": self.target.risk_summary,
            "quantity": self.quantity,
            "max_quantity": self.target.max_quantity,
            "outcomes": {
                branch.outcome.value: {"preview": branch.preview or branch.message}
                for branch in self.target.outcome_branches
            },
        }


@dataclass(frozen=True, slots=True)
class NpcOutcomeResolution:
    state: ExplorationState
    plan: NpcIntentActionPlan
    outcome: NpcOutcomeTier
    branch: NpcOutcomeBranch
    effect_results: tuple[ExplorationEffectResult, ...]


def plan_npc_intent_action(
    state: ExplorationState,
    *,
    permission: NpcIntentPermission,
    target_id: str,
    quantity: int = 1,
) -> NpcIntentActionPlan:
    target = permission.target(target_id)
    if target is None:
        raise ValueError(
            f"NPC intent {permission.intent} has no target: {target_id}."
        )
    if quantity < 1 or quantity > target.max_quantity:
        raise ValueError(
            f"NPC target {target.id} quantity must be in range 1..{target.max_quantity}."
        )
    missing_flags = [
        flag for flag in target.requires_flags if not scene_flag(state.flags, flag, False)
    ]
    if missing_flags:
        raise ValueError(
            f"NPC target {target.id} is locked by flags: {', '.join(missing_flags)}."
        )
    return NpcIntentActionPlan(permission.intent, target, quantity)


def npc_outcome_for_check(
    *,
    success: bool,
    natural_roll: int,
) -> NpcOutcomeTier:
    if success and natural_roll == 20:
        return NpcOutcomeTier.CRITICAL_SUCCESS
    if not success and natural_roll == 1:
        return NpcOutcomeTier.CRITICAL_FAILURE
    return NpcOutcomeTier.SUCCESS if success else NpcOutcomeTier.FAILURE


def resolve_npc_outcome(
    state: ExplorationState,
    plan: NpcIntentActionPlan,
    outcome: NpcOutcomeTier,
) -> NpcOutcomeResolution:
    branch = plan.target.branch(outcome)
    current = state
    results: list[ExplorationEffectResult] = []
    for effect in branch.effects:
        result = apply_exploration_effect(current, effect)
        current = result.state
        results.append(result)
    return NpcOutcomeResolution(current, plan, outcome, branch, tuple(results))


__all__ = [
    "NpcIntentActionPlan",
    "NpcOutcomeResolution",
    "npc_outcome_for_check",
    "plan_npc_intent_action",
    "resolve_npc_outcome",
]
