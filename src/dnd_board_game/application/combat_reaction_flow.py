from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from dnd_board_game.actors import Actor, ActorId
from dnd_board_game.combat import (
    ActionUse,
    ActiveCombatEffect,
    AppliedDamageResult,
    AttackDeclaration,
    AttackSource,
    CombatState,
    CombatStatus,
    DamageComponentInput,
    DamageType,
    EnemyAutoTurnResult,
    apply_damage_result,
    attack_source_with_target_combat_effects,
    actor_as_combat_target,
    consume_next_attack_effects,
    replace_actor,
    resolve_attack,
    resolve_damage,
    reaction_available_for,
    start_attack_action,
    use_actor_reaction,
    use_movement,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    D20RollResult,
    RollMode,
    resolve_d20_roll,
)
from dnd_board_game.world import BoardState, PathResult


@dataclass(frozen=True, slots=True)
class CombatReactionResolution:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    applied_damages: tuple[AppliedDamageResult, ...]
    movement_performed: bool
    message_title: str
    message_body: str


@dataclass(frozen=True, slots=True)
class PlayerReactionAttackResolution:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    source: AttackSource
    attack_roll: D20RollResult
    hit: bool
    critical: bool
    message: str


@dataclass(frozen=True, slots=True)
class PlayerReactionDamageResolution:
    state: CombatState
    applied_damage: AppliedDamageResult
    target_id: str


@dataclass(frozen=True, slots=True)
class ReadyAttackTrigger:
    readied_actor_id: str
    target_id: str
    effect_id: str
    trigger: str


class CombatReactionFlowService:
    """Resolve opportunity attacks before a pending player movement."""

    def resolve_opportunity_movement(
        self,
        *,
        state: CombatState,
        actor_id: str,
        path: PathResult,
        threat_actor_ids: tuple[str, ...],
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
        roll_d20: Callable[[D20RollRequest], D20RollInput],
        roll_damage: Callable[[int], int],
    ) -> CombatReactionResolution:
        actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
        if actor is None:
            raise ValueError("Aktor oczekującego ruchu nie istnieje.")

        messages: list[str] = []
        applied_damages: list[AppliedDamageResult] = []
        updated_state = state
        updated_effects = active_effects
        for attacker_id in threat_actor_ids:
            actor = next(
                (candidate for candidate in updated_state.actors if str(candidate.id) == actor_id),
                actor,
            )
            if actor.is_defeated():
                break
            attacker = next(
                (candidate for candidate in updated_state.actors if str(candidate.id) == attacker_id),
                None,
            )
            if attacker is None or attacker.is_defeated():
                continue
            source = attack_sources_by_actor.get(attacker.id)
            if source is None:
                continue
            reaction = use_actor_reaction(updated_state, attacker)
            if not reaction.accepted:
                continue
            updated_state = reaction.state
            actor = next(candidate for candidate in updated_state.actors if str(candidate.id) == actor_id)
            source = attack_source_with_target_combat_effects(attacker, actor, source, updated_effects)
            rolled_input = roll_d20(source.attack_roll_request)
            attack_roll = resolve_d20_roll(
                D20RollInput(
                    source.attack_roll_request,
                    rolled_input.natural_roll,
                    rolled_input.natural_roll_2,
                )
            )
            declaration = AttackDeclaration(
                attacker=attacker,
                target=actor_as_combat_target(actor),
                source=source,
            )
            resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
            updated_effects = consume_next_attack_effects(
                updated_effects,
                str(attacker.id),
                str(actor.id),
            )
            if resolution.hit:
                damage_amount = _opportunity_damage(source, roll_damage)
                damage_result = resolve_damage(
                    (DamageComponentInput(damage_amount, DamageType(source.damage_type), source.name),)
                )
                applied_damage = apply_damage_result(actor, damage_result)
                applied_damages.append(applied_damage)
                updated_state = replace_actor(updated_state, applied_damage.actor_after)
                defeated_text = " Cel zostaje pokonany." if applied_damage.defeated_by_damage else ""
                messages.append(
                    f"{attacker.name}: d20 {attack_roll.natural_roll}, razem {attack_roll.total}, trafienie. "
                    f"{_damage_application_message(applied_damage)}{defeated_text}"
                )
            else:
                messages.append(
                    f"{attacker.name}: d20 {attack_roll.natural_roll}, razem {attack_roll.total}, "
                    f"pudło przeciwko {actor.name}."
                )

        actor = next(
            (candidate for candidate in updated_state.actors if str(candidate.id) == actor_id),
            actor,
        )
        movement_performed = False
        if not actor.is_defeated() and updated_state.status == CombatStatus.ACTIVE:
            movement = use_movement(updated_state, actor, path)
            if not movement.accepted:
                raise ValueError(movement.message)
            updated_state = movement.state
            movement_performed = True
            messages.append(movement.message)
        elif actor.is_defeated():
            messages.append(f"{actor.name} pada przed wykonaniem ruchu.")

        message = " ".join(messages) if messages else "Brak dostępnych reakcji. Ruch zostaje wykonany."
        return CombatReactionResolution(
            state=updated_state,
            active_effects=updated_effects,
            applied_damages=tuple(applied_damages),
            movement_performed=movement_performed,
            message_title="Atak okazyjny",
            message_body=message,
        )


class PlayerReactionFlowService:
    """Resolve manually rolled hero reactions during an enemy turn."""

    def resolve_attack_roll(
        self,
        *,
        state: CombatState,
        attacker_id: str,
        target_id: str,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
        natural_roll: int,
        natural_roll_2: int | None = None,
        consumed_effect_id: str | None = None,
    ) -> PlayerReactionAttackResolution:
        attacker = _actor_by_string_id(state, attacker_id)
        target = _actor_by_string_id(state, target_id)
        source = attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        reaction = use_actor_reaction(state, attacker)
        if not reaction.accepted:
            raise ValueError(reaction.message)
        updated_state = reaction.state
        attacker = _actor_by_string_id(updated_state, attacker_id)
        target = _actor_by_string_id(updated_state, target_id)
        source = attack_source_with_target_combat_effects(
            attacker,
            target,
            source,
            active_effects,
        )
        attack_roll = resolve_d20_roll(
            _manual_d20_input(source.attack_roll_request, natural_roll, natural_roll_2)
        )
        declaration = AttackDeclaration(
            attacker=attacker,
            target=actor_as_combat_target(target),
            source=source,
        )
        resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
        updated_effects = active_effects
        if consumed_effect_id is not None:
            updated_effects = tuple(
                effect for effect in updated_effects if effect.id != consumed_effect_id
            )
        updated_effects = consume_next_attack_effects(
            updated_effects,
            attacker_id,
            target_id,
        )
        return PlayerReactionAttackResolution(
            state=updated_state,
            active_effects=updated_effects,
            source=source,
            attack_roll=attack_roll,
            hit=resolution.hit,
            critical=resolution.critical,
            message=_player_attack_message(
                attacker.name,
                target.name,
                attack_roll.total,
                resolution.hit,
                resolution.critical,
            ),
        )

    def apply_damage(
        self,
        *,
        state: CombatState,
        attacker_id: str,
        target_id: str,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
        damage: int,
    ) -> PlayerReactionDamageResolution:
        attacker = _actor_by_string_id(state, attacker_id)
        target = _actor_by_string_id(state, target_id)
        source = attack_sources_by_actor.get(attacker.id)
        if source is None:
            raise ValueError(f"Aktor {attacker.name} nie ma zdefiniowanego ataku.")
        source = attack_source_with_target_combat_effects(
            attacker,
            target,
            source,
            active_effects,
        )
        damage_result = resolve_damage(
            (
                DamageComponentInput(
                    max(0, int(damage)),
                    DamageType(source.damage_type),
                    source.name,
                ),
            )
        )
        applied_damage = apply_damage_result(target, damage_result)
        return PlayerReactionDamageResolution(
            state=replace_actor(state, applied_damage.actor_after),
            applied_damage=applied_damage,
            target_id=target_id,
        )

    def detect_ready_attack(
        self,
        *,
        state: CombatState,
        enemy_result: EnemyAutoTurnResult,
        board: BoardState,
        attack_sources_by_actor: Mapping[ActorId, AttackSource],
        active_effects: tuple[ActiveCombatEffect, ...],
    ) -> ReadyAttackTrigger | None:
        trigger = _ready_trigger_for_enemy_result(enemy_result)
        if trigger is None:
            return None
        trigger_target = enemy_result.moved_enemy or enemy_result.enemy
        if trigger_target.is_defeated():
            return None
        for effect in active_effects:
            if effect.kind != "ready_attack":
                continue
            if effect.object_id != f"combat_action:ready:{trigger}":
                continue
            readied_actor = next(
                (actor for actor in state.actors if str(actor.id) == effect.actor_id),
                None,
            )
            if readied_actor is None or readied_actor.is_defeated():
                continue
            if not reaction_available_for(state, readied_actor):
                continue
            source = attack_sources_by_actor.get(readied_actor.id)
            if source is None:
                continue
            legal_targets = start_attack_action(
                board,
                readied_actor,
                enemy_result.state.actors,
                source,
            ).legal_targets
            if any(target.id == str(trigger_target.id) for target in legal_targets):
                return ReadyAttackTrigger(
                    readied_actor_id=str(readied_actor.id),
                    target_id=str(trigger_target.id),
                    effect_id=effect.id,
                    trigger=trigger,
                )
        return None


def _opportunity_damage(
    source: AttackSource,
    roll_damage: Callable[[int], int],
) -> int:
    if source.damage_fixed is not None:
        return source.damage_fixed + source.damage_modifier
    die_sides = source.damage_die_sides or 6
    rolled = int(roll_damage(die_sides))
    if not 1 <= rolled <= die_sides:
        raise ValueError(f"Wynik kości obrażeń musi być w zakresie 1-{die_sides}.")
    return rolled + source.damage_modifier


def _ready_trigger_for_enemy_result(result: EnemyAutoTurnResult) -> str | None:
    if (
        result.movement_path is not None
        and result.movement_path.valid
        and result.movement_path.destination != result.movement_path.origin
    ):
        return "enemy_moves"
    if result.target is not None:
        return "enemy_attacks"
    return None


def _actor_by_string_id(state: CombatState, actor_id: str) -> Actor:
    actor = next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor


def _manual_d20_input(
    request: D20RollRequest,
    natural_roll: int,
    natural_roll_2: int | None,
) -> D20RollInput:
    if request.mode == RollMode.NORMAL:
        return D20RollInput(request, int(natural_roll))
    if natural_roll_2 is None:
        raise ValueError("Ten rzut wymaga wpisania dwóch wyników d20.")
    return D20RollInput(request, int(natural_roll), int(natural_roll_2))


def _player_attack_message(
    attacker_name: str,
    target_name: str,
    total: int,
    hit: bool,
    critical: bool,
) -> str:
    if critical:
        return f"{attacker_name} trafia krytycznie {target_name}. Wynik ataku: {total}."
    if hit:
        return f"{attacker_name} trafia {target_name}. Wynik ataku: {total}."
    return f"{attacker_name} pudłuje przeciwko {target_name}. Wynik ataku: {total}."


def _damage_application_message(result: AppliedDamageResult) -> str:
    defeated_text = " Cel zostaje pokonany." if result.defeated_by_damage else ""
    temp_text = ""
    if result.temp_hp_before > 0 or result.absorbed_by_temp_hp > 0:
        temp_text = (
            f" Temp HP {result.temp_hp_before} -> {result.temp_hp_after}, "
            f"pochłonięto {result.absorbed_by_temp_hp}."
        )
    return (
        f"Obrażenia: {result.damage.total_applied}. "
        f"{result.actor_before.name}: HP {result.hp_before} -> {result.hp_after} / "
        f"{result.actor_after.max_hp}.{temp_text}{defeated_text}"
    )
