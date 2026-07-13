from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.exploration import (
    ExplorationEffectResult,
    ExplorationState,
    ExplorationZone,
    ShortRestPolicy,
    apply_exploration_effect,
)
from dnd_board_game.rules import (
    ActiveEffect,
    EffectEvent,
    EffectEventType,
    HitDieSpendResult,
    RestResult,
    complete_short_rest,
    expire_active_effects,
    spend_hit_die,
)


@dataclass(frozen=True, slots=True)
class PendingShortRest:
    policy: ShortRestPolicy
    zone_id: str
    completed: bool = False


@dataclass(frozen=True, slots=True)
class ShortRestCompletionTransition:
    state: ExplorationState
    actors: tuple[Actor, ...]
    pending: PendingShortRest
    rest_results: tuple[RestResult, ...]
    effects: tuple[ExplorationEffectResult, ...]
    active_effects: tuple[ActiveEffect, ...]
    expired_effects: tuple[ActiveEffect, ...]


@dataclass(frozen=True, slots=True)
class ShortRestHitDieTransition:
    actors: tuple[Actor, ...]
    result: HitDieSpendResult


class ShortRestFlowService:
    """Coordinates a content-driven short rest without owning UI state."""

    def start(
        self,
        *,
        state: ExplorationState,
        zone: ExplorationZone,
        encounter_pending: bool,
    ) -> PendingShortRest:
        if encounter_pending:
            raise ValueError("Nie można odpocząć, gdy encounter czeka na rozpoczęcie.")
        policy = zone.short_rest_policy
        if policy is None:
            raise ValueError("W tej lokacji nie ma warunków do krótkiego odpoczynku.")
        completed = short_rest_count(state, policy.id)
        if policy.max_completions and completed >= policy.max_completions:
            raise ValueError("Drużyna wykorzystała już możliwość odpoczynku w tej lokacji.")
        return PendingShortRest(policy=policy, zone_id=zone.id)

    def complete(
        self,
        *,
        state: ExplorationState,
        actors: tuple[Actor, ...],
        pending: PendingShortRest,
        active_effects: tuple[ActiveEffect, ...] = (),
    ) -> ShortRestCompletionTransition:
        if pending.completed:
            raise ValueError("Ten krótki odpoczynek został już ukończony.")
        if state.party_position.zone_id != pending.zone_id:
            raise ValueError("Drużyna opuściła miejsce wybranego odpoczynku.")
        rest_results = tuple(
            complete_short_rest(actor)
            for actor in actors
            if actor.faction == Faction.ALLY
        )
        actors_by_id = {result.actor_after.id: result.actor_after for result in rest_results}
        updated_actors = tuple(actors_by_id.get(actor.id, actor) for actor in actors)
        updated_state = replace(
            state,
            elapsed_minutes=state.elapsed_minutes + pending.policy.duration_minutes,
            short_rest_counts=_increment_short_rest_count(
                state.short_rest_counts,
                pending.policy.id,
            ),
        )
        effects: list[ExplorationEffectResult] = []
        for raw_effect in pending.policy.completion_effects:
            effect = apply_exploration_effect(updated_state, raw_effect)
            updated_state = effect.state
            effects.append(effect)
        expiration = expire_active_effects(
            active_effects,
            EffectEvent(EffectEventType.SHORT_REST_COMPLETED),
        )
        return ShortRestCompletionTransition(
            state=updated_state,
            actors=updated_actors,
            pending=replace(pending, completed=True),
            rest_results=rest_results,
            effects=tuple(effects),
            active_effects=expiration.active_effects,
            expired_effects=expiration.expired_effects,
        )

    def spend_hit_die(
        self,
        *,
        actors: tuple[Actor, ...],
        actor_id: str,
        die_sides: int,
        natural_roll: int,
    ) -> ShortRestHitDieTransition:
        actor = next((candidate for candidate in actors if str(candidate.id) == actor_id), None)
        if actor is None or actor.faction != Faction.ALLY:
            raise ValueError("Nieznany bohater odpoczywający.")
        result = spend_hit_die(actor, die_sides=die_sides, natural_roll=natural_roll)
        updated = tuple(result.actor_after if candidate.id == actor.id else candidate for candidate in actors)
        return ShortRestHitDieTransition(updated, result)


def short_rest_count(state: ExplorationState, policy_id: str) -> int:
    return next((count for rest_id, count in state.short_rest_counts if rest_id == policy_id), 0)


def _increment_short_rest_count(
    counts: tuple[tuple[str, int], ...],
    policy_id: str,
) -> tuple[tuple[str, int], ...]:
    values = dict(counts)
    values[policy_id] = values.get(policy_id, 0) + 1
    return tuple(sorted(values.items()))
