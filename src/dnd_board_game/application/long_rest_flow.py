"""Content-gated party long rests."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import ConditionState, TriggerActivation, resolve_actor_trigger_events
from dnd_board_game.exploration import (
    ExplorationEffectResult,
    ExplorationState,
    ExplorationZone,
    LongRestPolicy,
    ScenarioClockEvent,
    TimedMagicEffect,
    advance_exploration_time,
    apply_exploration_effect,
)
from dnd_board_game.rules import (
    ActiveEffect,
    EffectEvent,
    EffectEventType,
    RestResult,
    complete_long_rest,
    expire_active_effects,
)

from .effect_boundary_flow import expire_exploration_conditions


@dataclass(frozen=True, slots=True)
class LongRestTransition:
    state: ExplorationState
    actors: tuple[Actor, ...]
    policy: LongRestPolicy
    rest_results: tuple[RestResult, ...]
    effects: tuple[ExplorationEffectResult, ...]
    active_effects: tuple[ActiveEffect, ...]
    expired_effects: tuple[ActiveEffect, ...]
    expired_conditions: tuple[ConditionState, ...]
    expired_magic_effects: tuple[TimedMagicEffect, ...]
    triggered_clock_events: tuple[ScenarioClockEvent, ...]
    trigger_activations: tuple[TriggerActivation, ...]


class LongRestFlowService:
    def complete(
        self,
        *,
        state: ExplorationState,
        zone: ExplorationZone,
        actors: tuple[Actor, ...],
        encounter_pending: bool,
        active_effects: tuple[ActiveEffect, ...] = (),
        roll_die: Callable[[int], int] | None = None,
    ) -> LongRestTransition:
        if encounter_pending:
            raise ValueError("Nie można odpocząć, gdy encounter czeka na rozpoczęcie.")
        policy = zone.long_rest_policy
        if policy is None:
            raise ValueError("W tej lokacji nie ma warunków do długiego odpoczynku.")
        completed = rest_policy_count(state, policy.id)
        if policy.max_completions and completed >= policy.max_completions:
            raise ValueError("Długi odpoczynek w tej lokacji został już wykorzystany.")
        allied = tuple(actor for actor in actors if actor.faction == Faction.ALLY)
        if any(actor.hp <= 0 for actor in allied):
            raise ValueError("Każdy odpoczywający bohater musi mieć co najmniej 1 PW.")
        rest_results = tuple(complete_long_rest(actor, roll_die=roll_die) for actor in allied)
        recovered = {result.actor_after.id: result.actor_after for result in rest_results}
        updated_actors = tuple(recovered.get(actor.id, actor) for actor in actors)
        updated_state = replace(
            state,
            short_rest_counts=_increment_rest_count(state.short_rest_counts, policy.id),
        )
        time_advance = advance_exploration_time(updated_state, policy.duration_minutes)
        updated_state, condition_expiration = expire_exploration_conditions(
            time_advance.state,
            EffectEvent(EffectEventType.LONG_REST_COMPLETED),
        )
        effects: list[ExplorationEffectResult] = []
        for raw_effect in policy.completion_effects:
            result = apply_exploration_effect(updated_state, raw_effect)
            updated_state = result.state
            effects.append(result)
        expiration = expire_active_effects(
            active_effects,
            EffectEvent(EffectEventType.LONG_REST_COMPLETED),
        )
        trigger_resolution = resolve_actor_trigger_events(
            updated_actors,
            (
                EffectEvent(EffectEventType.LONG_REST_COMPLETED, actor_id=str(actor.id))
                for actor in updated_actors
            ),
        )
        return LongRestTransition(
            state=updated_state,
            actors=trigger_resolution.actors,
            policy=policy,
            rest_results=rest_results,
            effects=tuple(effects),
            active_effects=expiration.active_effects,
            expired_effects=expiration.expired_effects,
            expired_conditions=condition_expiration.expired_conditions,
            expired_magic_effects=time_advance.expired_effects,
            triggered_clock_events=time_advance.triggered_clock_events,
            trigger_activations=trigger_resolution.activations,
        )


def rest_policy_count(state: ExplorationState, policy_id: str) -> int:
    return next((count for rest_id, count in state.short_rest_counts if rest_id == policy_id), 0)


def _increment_rest_count(
    counts: tuple[tuple[str, int], ...], policy_id: str
) -> tuple[tuple[str, int], ...]:
    values = dict(counts)
    values[policy_id] = values.get(policy_id, 0) + 1
    return tuple(sorted(values.items()))


__all__ = ["LongRestFlowService", "LongRestTransition", "rest_policy_count"]
