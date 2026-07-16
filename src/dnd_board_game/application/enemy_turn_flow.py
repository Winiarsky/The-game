from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from random import Random
from typing import Mapping

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    ActiveCombatEffect,
    AttackSource,
    CombatState,
    CombatStatus,
    EnemyAutoTurnResult,
    EnemyTurnPlan,
    SceneObject,
    DamageComponentInput,
    DamageType,
    apply_damage_result,
    apply_save_damage_amount,
    attack_source_with_target_combat_effects,
    current_actor,
    opportunity_attackers_for_movement,
    plan_enemy_turn,
    resolve_enemy_auto_turn,
    resolve_actor_saving_throw,
    resolve_damage,
    replace_actor,
)
from dnd_board_game.rules import SavingThrowRequest, SavingThrowResult
from dnd_board_game.world import BoardState, Coordinate

from .combat_reaction_flow import PlayerReactionFlowService, ReadyAttackTrigger
from .damage_presentation import applied_damage_message, applied_damage_payload


class EnemyTurnTransitionKind(StrEnum):
    READY = "ready"
    OPPORTUNITY = "opportunity"
    MOVEMENT = "movement"
    ATTACK = "attack"
    FINISHED = "finished"


@dataclass(frozen=True, slots=True)
class EnemyTurnIntentTransition:
    intent: EnemyTurnPlan
    enemy_id: str
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


@dataclass(frozen=True, slots=True)
class EnemyTurnResolutionTransition:
    result: EnemyAutoTurnResult
    kind: EnemyTurnTransitionKind
    board_message: str
    message_title: str
    message_body: str
    ready_trigger: ReadyAttackTrigger | None = None
    threat_actor_ids: tuple[str, ...] = ()
    event_type: str = ""
    event_payload: tuple[tuple[str, object], ...] = ()


@dataclass(frozen=True, slots=True)
class PendingEnemySavingThrow:
    target_id: str
    source_id: str
    request: SavingThrowRequest


@dataclass(frozen=True, slots=True)
class EnemySavingThrowTransition:
    result: EnemyAutoTurnResult
    saving_throw: SavingThrowResult
    board_message: str
    message_title: str
    message_body: str
    event_type: str
    event_payload: tuple[tuple[str, object], ...]


class EnemyTurnFlowService:
    """Plan and classify enemy turns before UI and board confirmation."""

    def __init__(self) -> None:
        self._player_reactions = PlayerReactionFlowService()

    def plan(
        self,
        *,
        state: CombatState,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        multiattack_sources_by_actor: Mapping[ActorId, tuple[AttackSource, ...]] | None = None,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> EnemyTurnIntentTransition:
        enemy = _active_enemy(state)
        source = _enemy_attack_source(
            state,
            enemy,
            attack_sources_by_actor,
            multiattack_sources_by_actor,
        )
        if source is None:
            raise ValueError(f"Aktor {enemy.name} nie ma zdefiniowanego ataku.")
        intent = plan_enemy_turn(board, state, enemy, source)
        return EnemyTurnIntentTransition(
            intent=intent,
            enemy_id=str(enemy.id),
            board_message=intent.message,
            message_title="Zamiar przeciwnika",
            message_body=f"{intent.message} Potwierdź Enterem albo przyciskiem.",
            event_type="ui_combat_enemy_turn_intent",
            event_payload=(
                ("enemy_id", str(enemy.id)),
                ("target_id", intent.target.id if intent.target is not None else None),
                ("message", intent.message),
            ),
        )

    def resolve(
        self,
        *,
        state: CombatState,
        intent: EnemyTurnPlan,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        multiattack_sources_by_actor: Mapping[ActorId, tuple[AttackSource, ...]] | None = None,
        active_effects: tuple[ActiveCombatEffect, ...],
        rng: Random,
        scene_objects: tuple[SceneObject, ...] = (),
    ) -> EnemyTurnResolutionTransition:
        enemy = _active_enemy(state)
        source = _enemy_attack_source(
            state,
            enemy,
            attack_sources_by_actor,
            multiattack_sources_by_actor,
        )
        if source is None:
            raise ValueError(f"Aktor {enemy.name} nie ma zdefiniowanego ataku.")
        target_actor = None
        if intent.target is not None:
            target_actor = next(
                (actor for actor in state.actors if str(actor.id) == intent.target.id),
                None,
            )
        if target_actor is not None:
            source = attack_source_with_target_combat_effects(
                enemy,
                target_actor,
                source,
                active_effects,
            )
        result = resolve_enemy_auto_turn(
            board,
            state,
            enemy,
            source,
            rng,
            scene_objects,
            maximum_attacks=(
                len(multiattack_sources_by_actor.get(enemy.id, ()))
                if multiattack_sources_by_actor
                and multiattack_sources_by_actor.get(enemy.id)
                else None
            ),
        )
        ready = self._player_reactions.detect_ready_attack(
            state=state,
            enemy_result=result,
            board=board,
            attack_sources_by_actor=attack_sources_by_actor,
            active_effects=active_effects,
        )
        if ready is not None:
            readied_actor = next(
                actor for actor in state.actors if str(actor.id) == ready.readied_actor_id
            )
            return EnemyTurnResolutionTransition(
                result=result,
                kind=EnemyTurnTransitionKind.READY,
                ready_trigger=ready,
                board_message=(
                    f"Wyzwolono Ready: {readied_actor.name} może użyć przygotowanego ataku."
                ),
                message_title="Ready",
                message_body=(
                    f"{readied_actor.name}: warunek przygotowanej akcji został spełniony "
                    f"({_ready_trigger_label(ready.trigger)})."
                ),
                event_type="ui_combat_ready_triggered",
                event_payload=(
                    ("readied_actor_id", ready.readied_actor_id),
                    ("target_id", ready.target_id),
                    ("trigger", ready.trigger),
                ),
            )
        if _result_has_movement(result, enemy.position):
            threats = tuple(
                threat
                for threat in opportunity_attackers_for_movement(
                    state,
                    enemy,
                    enemy.position,
                    result.movement_path.destination,
                    attack_sources_by_actor,
                    active_effects,
                )
                if threat.attacker.faction == Faction.ALLY
            )
            if threats:
                threat_actor_ids = tuple(str(threat.attacker.id) for threat in threats)
                threat_names = ", ".join(threat.attacker.name for threat in threats)
                return EnemyTurnResolutionTransition(
                    result=result,
                    kind=EnemyTurnTransitionKind.OPPORTUNITY,
                    threat_actor_ids=threat_actor_ids,
                    board_message=(
                        f"{enemy.name} opuszcza zasięg: {threat_names}. "
                        "Wybierz atak okazyjny albo pomiń reakcję."
                    ),
                    message_title="Atak okazyjny",
                    message_body=(
                        f"{enemy.name} prowokuje atak okazyjny. "
                        f"Reakcję może wykonać: {threat_names}."
                    ),
                    event_type="ui_combat_enemy_opportunity_pending",
                    event_payload=(
                        ("enemy_id", str(enemy.id)),
                        (
                            "destination",
                            [result.movement_path.destination.col, result.movement_path.destination.row],
                        ),
                        ("threat_actor_ids", list(threat_actor_ids)),
                    ),
                )
            destination = result.movement_path.destination
            return EnemyTurnResolutionTransition(
                result=result,
                kind=EnemyTurnTransitionKind.MOVEMENT,
                board_message=(
                    f"{enemy.name} rusza na {destination.as_tuple()}. "
                    "Przestaw figurkę po podświetlonej ścieżce i kliknij pole docelowe."
                ),
                message_title="Ruch przeciwnika",
                message_body=(
                    f"{enemy.name} planuje ruch na {destination.as_tuple()}. "
                    "Potwierdź pole docelowe na planszy."
                ),
            )
        if result.target is not None:
            if result.saving_throw_request is not None:
                request = result.saving_throw_request
                ability_label = request.as_payload()["ability_label"]
                return EnemyTurnResolutionTransition(
                    result=result,
                    kind=EnemyTurnTransitionKind.ATTACK,
                    board_message=(
                        f"{enemy.name} używa {source.name} przeciw {result.target.name}. "
                        "Kliknij podświetlone pole celu, żeby potwierdzić efekt."
                    ),
                    message_title="Efekt przeciwnika",
                    message_body=(
                        f"{enemy.name} używa {source.name} przeciw {result.target.name}. "
                        f"Po potwierdzeniu celu {result.target.name} wykona "
                        f"{ability_label} save przeciw ST {request.dc}."
                    ),
                )
            return EnemyTurnResolutionTransition(
                result=result,
                kind=EnemyTurnTransitionKind.ATTACK,
                board_message=(
                    f"{enemy.name} atakuje {result.target.name}. "
                    "Kliknij podświetlone pole celu, żeby potwierdzić atak."
                ),
                message_title="Atak przeciwnika",
                message_body=(
                    f"{enemy.name} atakuje {result.target.name}. {_enemy_roll_summary(result)} "
                    "Potwierdź atak klikając pole celu."
                ),
            )
        return EnemyTurnResolutionTransition(
            result=result,
            kind=EnemyTurnTransitionKind.FINISHED,
            board_message="",
            message_title="",
            message_body="",
        )

    def resolve_player_saving_throw(
        self,
        *,
        result: EnemyAutoTurnResult,
        natural_roll: int,
        natural_roll_2: int | None = None,
    ) -> EnemySavingThrowTransition:
        request = result.saving_throw_request
        source = result.source
        if request is None or source is None or result.target is None:
            raise ValueError("Tura przeciwnika nie oczekuje rzutu obronnego gracza.")
        target = next(
            (actor for actor in result.state.actors if str(actor.id) == result.target.id),
            None,
        )
        if target is None:
            raise ValueError("Nie znaleziono celu oczekującego rzutu obronnego.")
        saving_throw = resolve_actor_saving_throw(
            target,
            request,
            natural_roll=int(natural_roll),
            natural_roll_2=natural_roll_2,
            condition_states=result.state.condition_states,
            combat_actors=result.state.actors,
        )
        base_damage = max(0, int(result.base_damage or 0))
        adjusted_damage = apply_save_damage_amount(base_damage, saving_throw)
        damage = resolve_damage(
            (
                DamageComponentInput(
                    adjusted_damage,
                    DamageType(source.damage_type),
                    source.name,
                ),
            )
        )
        applied = apply_damage_result(target, damage)
        updated_state = replace_actor(result.state, applied.actor_after)
        outcome = "sukces" if saving_throw.success else "porażka"
        message = (
            f"{target.name}: {request.ability} save d20 {saving_throw.natural_roll}, "
            f"modyfikator {saving_throw.modifier:+d}, razem {saving_throw.total} przeciw "
            f"ST {request.dc}: {outcome}. {applied_damage_message(applied)}"
        )
        updated_result = replace(
            result,
            state=updated_state,
            message=f"{result.message} {message}",
            damage=applied.damage,
            applied_damage=applied,
            updated_target=applied.actor_after,
            saving_throw_result=saving_throw,
        )
        return EnemySavingThrowTransition(
            result=updated_result,
            saving_throw=saving_throw,
            board_message="Rzut obronny rozstrzygnięty. Potwierdź wynik tury przeciwnika.",
            message_title="Rzut obronny",
            message_body=message,
            event_type="ui_combat_enemy_saving_throw",
            event_payload=(
                ("enemy_id", str(result.enemy.id)),
                ("target_id", str(target.id)),
                ("source_id", source.id),
                ("saving_throw", saving_throw.as_payload()),
                ("base_damage", base_damage),
                ("damage_result", applied_damage_payload(applied)),
            ),
        )


def _enemy_attack_source(
    state: CombatState,
    enemy: Actor,
    attack_sources_by_actor: Mapping[ActorId, AttackSource],
    multiattack_sources_by_actor: Mapping[ActorId, tuple[AttackSource, ...]] | None,
) -> AttackSource | None:
    sequence = (
        multiattack_sources_by_actor.get(enemy.id, ())
        if multiattack_sources_by_actor is not None
        else ()
    )
    if not sequence:
        return attack_sources_by_actor.get(enemy.id)
    used = state.turn_action.attacks_used if state.turn_action.attack_action_active else 0
    return sequence[min(used, len(sequence) - 1)]


def _active_enemy(state: CombatState) -> Actor:
    if state.status != CombatStatus.ACTIVE:
        raise ValueError("Walka nie jest aktywna.")
    enemy = current_actor(state)
    if enemy.faction != Faction.ENEMY:
        raise ValueError("To nie jest tura przeciwnika.")
    return enemy


def _result_has_movement(result: EnemyAutoTurnResult, origin: Coordinate) -> bool:
    return bool(
        result.movement_path is not None
        and result.movement_path.valid
        and result.movement_path.destination != origin
    )


def _ready_trigger_label(trigger: str) -> str:
    return {
        "enemy_moves": "gdy przeciwnik się poruszy",
        "enemy_attacks": "gdy przeciwnik zaatakuje",
    }.get(trigger, trigger)


def _enemy_roll_summary(result: EnemyAutoTurnResult) -> str:
    if result.saving_throw_result is not None:
        save = result.saving_throw_result
        outcome = "sukces" if save.success else "porażka"
        parts = [
            f"Rzut obronny d20: {save.natural_roll}",
            f"modyfikator: {save.modifier:+d}",
            f"wynik końcowy: {save.total} przeciw ST {save.dc}: {outcome}",
        ]
        if result.damage is not None:
            parts.append(f"obrażenia: {result.damage.total_applied}")
        return ". ".join(parts) + "."
    if result.attack_roll is None or result.target is None:
        return ""
    natural_rolls = result.attack_roll.natural_rolls
    roll_text = (
        f"{' / '.join(str(value) for value in natural_rolls)} -> {result.attack_roll.natural_roll}"
        if len(natural_rolls) > 1
        else str(result.attack_roll.natural_roll)
    )
    parts = [f"Rzut d20: {roll_text}", f"wynik końcowy: {result.attack_roll.total}"]
    if result.attack_resolution is not None:
        parts.append("trafienie" if result.attack_resolution.hit else "pudło")
        if result.attack_resolution.critical:
            parts.append("krytyk")
    if result.damage is not None:
        parts.append(f"obrażenia: {result.damage.total_applied}")
    if result.applied_damage is not None:
        parts.append(
            f"HP celu: {result.applied_damage.hp_before} -> {result.applied_damage.hp_after}"
        )
        if result.applied_damage.defeated_by_damage:
            parts.append("cel pokonany")
    return ". ".join(parts) + "."


def enemy_turn_message(result: EnemyAutoTurnResult) -> str:
    summary = _enemy_roll_summary(result)
    if not summary:
        return result.message
    return f"{result.message} {summary}"
