from __future__ import annotations

from dataclasses import dataclass
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
    attack_source_with_target_combat_effects,
    current_actor,
    opportunity_attackers_for_movement,
    plan_enemy_turn,
    resolve_enemy_auto_turn,
)
from dnd_board_game.world import BoardState, Coordinate

from .combat_reaction_flow import PlayerReactionFlowService, ReadyAttackTrigger


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
    ) -> EnemyTurnIntentTransition:
        enemy = _active_enemy(state)
        if attack_sources_by_actor.get(enemy.id) is None:
            raise ValueError(f"Aktor {enemy.name} nie ma zdefiniowanego ataku.")
        intent = plan_enemy_turn(board, state, enemy)
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
        active_effects: tuple[ActiveCombatEffect, ...],
        rng: Random,
    ) -> EnemyTurnResolutionTransition:
        enemy = _active_enemy(state)
        source = attack_sources_by_actor.get(enemy.id)
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
        result = resolve_enemy_auto_turn(board, state, enemy, source, rng)
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
