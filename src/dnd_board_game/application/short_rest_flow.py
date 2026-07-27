from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Callable

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.combat import (
    ConditionState,
    TriggerActivation,
    resolve_actor_trigger_events,
)
from dnd_board_game.exploration import (
    ExplorationEffectResult,
    ExplorationState,
    ExplorationZone,
    ShortRestPolicy,
    ScenarioClockEvent,
    TimedMagicEffect,
    apply_exploration_effect,
    advance_exploration_time,
)
from dnd_board_game.inventory import (
    ItemAttunementChoice,
    ItemAttunementResult,
    apply_item_attunement,
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
from .effect_boundary_flow import expire_exploration_conditions


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
    expired_conditions: tuple[ConditionState, ...]
    expired_magic_effects: tuple[TimedMagicEffect, ...]
    triggered_clock_events: tuple[ScenarioClockEvent, ...]
    trigger_activations: tuple[TriggerActivation, ...]
    attunement_results: tuple[ItemAttunementResult, ...] = ()


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
        roll_die: Callable[[int], int] | None = None,
        attunement_choices: tuple[ItemAttunementChoice, ...] = (),
    ) -> ShortRestCompletionTransition:
        if pending.completed:
            raise ValueError("Ten krótki odpoczynek został już ukończony.")
        if state.party_position.zone_id != pending.zone_id:
            raise ValueError("Drużyna opuściła miejsce wybranego odpoczynku.")
        choices_by_actor: dict[str, ItemAttunementChoice] = {}
        for choice in attunement_choices:
            if choice.actor_id in choices_by_actor:
                raise ValueError(
                    "Jeden bohater może zmienić tylko jedną więź podczas short resta."
                )
            choices_by_actor[choice.actor_id] = choice
        allied_ids = {
            str(actor.id)
            for actor in actors
            if actor.faction == Faction.ALLY
        }
        unknown_choice_ids = set(choices_by_actor) - allied_ids
        if unknown_choice_ids:
            raise ValueError("Wybrano attunement dla nieznanego bohatera.")
        actors_by_id = {str(actor.id): actor for actor in actors}
        for actor_id, choice in choices_by_actor.items():
            apply_item_attunement(
                actors_by_id[actor_id],
                item_id=choice.item_id,
                action=choice.action,
            )
        rest_results_list: list[RestResult] = []
        attunement_results: list[ItemAttunementResult] = []
        for actor in actors:
            if actor.faction != Faction.ALLY:
                continue
            rest_result = complete_short_rest(actor, roll_die=roll_die)
            choice = choices_by_actor.get(str(actor.id))
            if choice is not None:
                attunement = apply_item_attunement(
                    rest_result.actor_after,
                    item_id=choice.item_id,
                    action=choice.action,
                )
                attunement_results.append(attunement)
                rest_result = replace(rest_result, actor_after=attunement.actor)
            rest_results_list.append(rest_result)
        rest_results = tuple(rest_results_list)
        actors_by_id = {result.actor_after.id: result.actor_after for result in rest_results}
        updated_actors = tuple(actors_by_id.get(actor.id, actor) for actor in actors)
        updated_state = replace(
            state,
            short_rest_counts=_increment_short_rest_count(
                state.short_rest_counts,
                pending.policy.id,
            ),
        )
        time_advance = advance_exploration_time(
            updated_state,
            pending.policy.duration_minutes,
        )
        updated_state = time_advance.state
        updated_state, condition_expiration = expire_exploration_conditions(
            updated_state,
            EffectEvent(EffectEventType.SHORT_REST_COMPLETED),
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
        trigger_resolution = resolve_actor_trigger_events(
            updated_actors,
            (
                EffectEvent(EffectEventType.SHORT_REST_COMPLETED, actor_id=str(actor.id))
                for actor in updated_actors
            ),
        )
        return ShortRestCompletionTransition(
            state=updated_state,
            actors=trigger_resolution.actors,
            pending=replace(pending, completed=True),
            rest_results=rest_results,
            effects=tuple(effects),
            active_effects=expiration.active_effects,
            expired_effects=expiration.expired_effects,
            expired_conditions=condition_expiration.expired_conditions,
            expired_magic_effects=time_advance.expired_effects,
            triggered_clock_events=time_advance.triggered_clock_events,
            trigger_activations=trigger_resolution.activations,
            attunement_results=tuple(attunement_results),
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
