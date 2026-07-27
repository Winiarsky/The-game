"""Transitions for effects crossing exploration, combat, rest, and scenario boundaries."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.combat import (
    CombatCondition,
    ConditionState,
    expire_condition_states,
)
from dnd_board_game.exploration import ExplorationState
from dnd_board_game.rules import EffectEvent, EffectEventType


@dataclass(frozen=True, slots=True)
class ConditionBoundaryTransition:
    condition_states: tuple[ConditionState, ...]
    expired_conditions: tuple[ConditionState, ...] = ()


def expire_exploration_conditions(
    state: ExplorationState,
    event: EffectEvent,
) -> tuple[ExplorationState, ConditionBoundaryTransition]:
    remaining, expired = expire_condition_states(state.condition_states, event)
    return (
        replace(state, condition_states=remaining),
        ConditionBoundaryTransition(remaining, expired),
    )


def reconcile_conditions_after_encounter(
    *,
    exploration_conditions: tuple[ConditionState, ...],
    combat_conditions: tuple[ConditionState, ...],
    exploration_actor_ids: frozenset[str],
    encounter_actor_ids: frozenset[str],
) -> ConditionBoundaryTransition:
    """Expire encounter-local conditions and return valid persistent actor conditions."""

    remaining, expired = expire_condition_states(
        combat_conditions,
        EffectEvent(EffectEventType.ENCOUNTER_ENDED),
    )
    invalid_grapples = tuple(
        condition
        for condition in remaining
        if condition.condition == CombatCondition.GRAPPLED
        and condition.source_actor_id not in exploration_actor_ids
    )
    invalid_ids = {id(condition) for condition in invalid_grapples}
    transferable = tuple(
        condition
        for condition in remaining
        if condition.actor_id in exploration_actor_ids
        and id(condition) not in invalid_ids
    )
    preserved = tuple(
        condition
        for condition in exploration_conditions
        if condition.actor_id not in encounter_actor_ids
    )
    return ConditionBoundaryTransition(
        condition_states=(*preserved, *transferable),
        expired_conditions=(*expired, *invalid_grapples),
    )


__all__ = [
    "ConditionBoundaryTransition",
    "expire_exploration_conditions",
    "reconcile_conditions_after_encounter",
]
