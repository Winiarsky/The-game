from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Callable

from dnd_board_game.actors import (
    Actor,
    ActorResourceRechargeResult,
    actor_resource_pool,
    depleted_recharge_resource_ids,
    resolve_actor_resource_recharge,
)
from dnd_board_game.combat import (
    ActiveCombatEffect,
    CombatState,
    CombatStatus,
    EnemyAutoTurnResult,
    TriggerActivation,
    consume_next_attack_effects,
    current_actor,
    expire_turn_end_effects,
    expire_turn_start_effects,
    expire_condition_states,
    finish_turn,
    resolve_combat_triggers,
    replace_actor,
)
from dnd_board_game.rules import EffectEvent, EffectEventType, expire_active_effects

from .enemy_turn_flow import enemy_turn_message


@dataclass(frozen=True, slots=True)
class ExpiredCombatEffects:
    message_prefix: str
    effects: tuple[ActiveCombatEffect, ...]


@dataclass(frozen=True, slots=True)
class EnemyTurnCommitTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    result: EnemyAutoTurnResult
    board_message: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class CombatTurnFinalizationTransition:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    ending_actor: Actor
    expired_effects: tuple[ExpiredCombatEffects, ...]
    trigger_activations: tuple[TriggerActivation, ...]
    recharge_results: tuple[ActorResourceRechargeResult, ...]
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


class CombatTurnFinalizationService:
    """Commit results and advance turns without UI or board side effects."""

    def commit_enemy_result(
        self,
        *,
        result: EnemyAutoTurnResult,
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> EnemyTurnCommitTransition:
        updated_effects = active_effects
        if result.attack_roll is not None:
            updated_effects = consume_next_attack_effects(
                active_effects,
                str(result.enemy.id),
                result.target.id if result.target is not None else None,
            )
        message = enemy_turn_message(result)
        return EnemyTurnCommitTransition(
            state=result.state,
            active_effects=updated_effects,
            result=result,
            board_message=(
                "Wynik tury przeciwnika gotowy. Potwierdź Enterem albo przyciskiem w UI."
            ),
            event_type="ui_combat_enemy_turn_board_confirmed",
            event_payload=(
                ("enemy_id", str(result.enemy.id)),
                ("target_id", result.target.id if result.target is not None else None),
                ("message", message),
                ("source_id", result.source.id if result.source is not None else None),
                (
                    "resource_pool_id",
                    result.source.resource_pool_id if result.source is not None else None,
                ),
                (
                    "resource_cost",
                    result.source.resource_cost
                    if result.source is not None and result.source.resource_pool_id is not None
                    else 0,
                ),
            ),
        )

    def finalize_enemy_turn(
        self,
        *,
        result: EnemyAutoTurnResult,
        active_effects: tuple[ActiveCombatEffect, ...],
        roll_recharge: Callable[[int], int] | None = None,
    ) -> CombatTurnFinalizationTransition:
        message = enemy_turn_message(result)
        state, effects, expired, triggers, recharges = _advance_turn(
            result.state,
            result.enemy,
            active_effects,
            roll_recharge,
        )
        return CombatTurnFinalizationTransition(
            state=state,
            active_effects=effects,
            ending_actor=result.enemy,
            expired_effects=expired,
            trigger_activations=triggers,
            recharge_results=recharges,
            message_title="Tura przeciwnika",
            message_body=message,
            event_type="ui_combat_enemy_turn",
            event_payload=(
                ("enemy_id", str(result.enemy.id)),
                ("target_id", result.target.id if result.target is not None else None),
                ("message", message),
                ("action_used", result.action_used),
            ),
        )

    def finish_active_turn(
        self,
        *,
        state: CombatState,
        active_effects: tuple[ActiveCombatEffect, ...],
        roll_recharge: Callable[[int], int] | None = None,
    ) -> CombatTurnFinalizationTransition | None:
        if state.status != CombatStatus.ACTIVE:
            return None
        actor = current_actor(state)
        updated_state, updated_effects, expired, triggers, recharges = _advance_turn(
            state,
            actor,
            active_effects,
            roll_recharge,
        )
        return CombatTurnFinalizationTransition(
            state=updated_state,
            active_effects=updated_effects,
            ending_actor=actor,
            expired_effects=expired,
            trigger_activations=triggers,
            recharge_results=recharges,
            message_title="Koniec tury",
            message_body=f"Zakończono turę: {actor.name}.",
            event_type="ui_combat_turn_finished",
            event_payload=(("actor_id", str(actor.id)),),
        )


def _advance_turn(
    state: CombatState,
    ending_actor: Actor,
    active_effects: tuple[ActiveCombatEffect, ...],
    roll_recharge: Callable[[int], int] | None,
) -> tuple[
    CombatState,
    tuple[ActiveCombatEffect, ...],
    tuple[ExpiredCombatEffects, ...],
    tuple[TriggerActivation, ...],
    tuple[ActorResourceRechargeResult, ...],
]:
    end_event = EffectEvent(EffectEventType.TURN_END, actor_id=str(ending_actor.id))
    end_triggers = resolve_combat_triggers(state, end_event)
    state = end_triggers.state
    after_end = expire_turn_end_effects(active_effects, str(ending_actor.id))
    condition_states, _ = expire_condition_states(
        state.condition_states,
        end_event,
    )
    state = replace(state, condition_states=condition_states)
    notices: list[ExpiredCombatEffects] = []
    trigger_activations = list(end_triggers.activations)
    recharge_results: list[ActorResourceRechargeResult] = []
    expired_at_end = _removed_effects(active_effects, after_end)
    if expired_at_end:
        notices.append(
            ExpiredCombatEffects(
                f"Wygasły efekty końca tury: {ending_actor.name}",
                expired_at_end,
            )
        )

    updated_state = finish_turn(state)
    updated_effects = after_end
    if updated_state.round_number > state.round_number:
        after_round = expire_active_effects(
            updated_effects,
            EffectEvent(EffectEventType.ROUND_ENDED),
        ).active_effects
        expired_at_round = _removed_effects(updated_effects, after_round)
        if expired_at_round:
            notices.append(
                ExpiredCombatEffects(
                    f"Wygasły efekty końca rundy {state.round_number}",
                    expired_at_round,
                )
            )
        updated_effects = after_round
    if updated_state.status == CombatStatus.ACTIVE:
        starting_actor = current_actor(updated_state)
        condition_states, _ = expire_condition_states(
            updated_state.condition_states,
            EffectEvent(EffectEventType.TURN_START, actor_id=str(starting_actor.id)),
        )
        updated_state = replace(updated_state, condition_states=condition_states)
        after_start = expire_turn_start_effects(updated_effects, str(starting_actor.id))
        expired_at_start = _removed_effects(updated_effects, after_start)
        if expired_at_start:
            notices.append(
                ExpiredCombatEffects(
                    f"Wygasły efekty początku tury: {starting_actor.name}",
                    expired_at_start,
                )
            )
        updated_effects = after_start
        if roll_recharge is not None:
            for resource_id in depleted_recharge_resource_ids(starting_actor):
                pool = actor_resource_pool(starting_actor, resource_id)
                assert pool is not None and pool.recharge is not None
                recharge = resolve_actor_resource_recharge(
                    starting_actor,
                    resource_id,
                    roll_recharge(pool.recharge.die_sides),
                )
                recharge_results.append(recharge)
                starting_actor = recharge.actor_after
                updated_state = replace_actor(updated_state, starting_actor)
        start_event = EffectEvent(
            EffectEventType.TURN_START,
            actor_id=str(starting_actor.id),
        )
        start_triggers = resolve_combat_triggers(updated_state, start_event)
        updated_state = start_triggers.state
        trigger_activations.extend(start_triggers.activations)
    return (
        updated_state,
        updated_effects,
        tuple(notices),
        tuple(trigger_activations),
        tuple(recharge_results),
    )


def _removed_effects(
    before: tuple[ActiveCombatEffect, ...],
    after: tuple[ActiveCombatEffect, ...],
) -> tuple[ActiveCombatEffect, ...]:
    after_ids = {effect.id for effect in after}
    return tuple(effect for effect in before if effect.id not in after_ids)
