from __future__ import annotations

import random
from dataclasses import dataclass, replace

from dnd_board_game.actors import Actor
from dnd_board_game.rules import D20RollInput, D20RollResult, resolve_d20_roll
from dnd_board_game.world import BoardState, PathResult, find_path, movement_range

from .action_economy import ActionUse
from .attack_flow import AttackDeclaration, AttackResolution, AttackSource, legal_melee_targets, resolve_attack
from .damage import DamageComponentInput, DamageResult, DamageType, apply_damage, resolve_damage
from .session import CombatState, replace_actor, use_movement, use_turn_action
from .targets import CombatTarget


@dataclass(frozen=True, slots=True)
class EnemyAutoAttackResult:
    state: CombatState
    enemy: Actor
    target: CombatTarget | None
    message: str
    attack_roll: D20RollResult | None = None
    attack_resolution: AttackResolution | None = None
    damage: DamageResult | None = None
    updated_target: Actor | None = None
    action_used: bool = False


@dataclass(frozen=True, slots=True)
class EnemyAutoTurnResult:
    state: CombatState
    enemy: Actor
    target: CombatTarget | None
    message: str
    movement_path: PathResult | None = None
    moved_enemy: Actor | None = None
    attack_roll: D20RollResult | None = None
    attack_resolution: AttackResolution | None = None
    damage: DamageResult | None = None
    updated_target: Actor | None = None
    action_used: bool = False


def resolve_enemy_auto_attack(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    rng: random.Random,
) -> EnemyAutoAttackResult:
    action_result = use_turn_action(state)
    if not action_result.accepted:
        return EnemyAutoAttackResult(action_result.state, enemy, None, action_result.message, action_used=False)

    targets = legal_melee_targets(board, enemy, action_result.state.actors)
    if not targets:
        return EnemyAutoAttackResult(
            action_result.state,
            enemy,
            None,
            f"{enemy.name} nie ma legalnego celu ataku i kończy akcję.",
            action_used=True,
        )

    target = _select_enemy_target(enemy, targets)
    attack_roll = resolve_d20_roll(D20RollInput(source.attack_roll_request, rng.randint(1, 20)))
    declaration = AttackDeclaration(attacker=enemy, target=target, source=source)
    resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
    updated_state = action_result.state
    damage: DamageResult | None = None
    updated_target: Actor | None = None

    if resolution.hit:
        if source.damage_fixed is not None:
            damage_amount = source.damage_fixed + source.damage_modifier
        else:
            die_sides = source.damage_die_sides or 6
            damage_amount = rng.randint(1, die_sides) + source.damage_modifier
        damage_type = DamageType(source.damage_type)
        damage = resolve_damage((DamageComponentInput(damage_amount, damage_type, source.name),))
        target_actor = _actor_for_target(action_result.state, target)
        updated_target = apply_damage(target_actor, damage)
        updated_state = replace_actor(action_result.state, updated_target)
        message = (
            f"{enemy.name} trafia {target.name}. Wynik ataku: {attack_roll.total}. "
            f"Obrażenia: {damage.total_applied} {damage_type.value}."
        )
    else:
        message = f"{enemy.name} pudłuje przeciwko {target.name}. Wynik ataku: {attack_roll.total}."

    return EnemyAutoAttackResult(
        state=updated_state,
        enemy=enemy,
        target=target,
        message=message,
        attack_roll=attack_roll,
        attack_resolution=resolution,
        damage=damage,
        updated_target=updated_target,
        action_used=True,
    )


def resolve_enemy_auto_turn(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    rng: random.Random,
) -> EnemyAutoTurnResult:
    targets = legal_melee_targets(board, enemy, state.actors)
    if targets:
        attack = resolve_enemy_auto_attack(board, state, enemy, source, rng)
        return _turn_result_from_attack(attack)

    movement_path = _best_enemy_movement_path(board, state, enemy)
    moved_enemy: Actor | None = None
    moved_state = state
    movement_message = f"{enemy.name} nie ma legalnego celu ataku."
    if movement_path is not None and movement_path.valid and movement_path.destination != enemy.position:
        movement = use_movement(state, enemy, movement_path)
        moved_state = movement.state
        moved_enemy = _actor_for_id(moved_state, enemy.id)
        movement_message = f"{enemy.name} rusza się na {movement_path.destination.as_tuple()}."
    else:
        action_result = use_turn_action(state)
        return EnemyAutoTurnResult(
            action_result.state,
            enemy,
            None,
            f"{enemy.name} nie ma legalnego celu ani dostępnego ruchu i kończy akcję.",
            action_used=action_result.accepted,
        )

    follow_up = resolve_enemy_auto_attack(board, moved_state, moved_enemy, source, rng)
    if follow_up.target is None:
        return EnemyAutoTurnResult(
            follow_up.state,
            moved_enemy,
            None,
            f"{movement_message} Po ruchu nadal nie ma legalnego celu ataku.",
            movement_path=movement_path,
            moved_enemy=moved_enemy,
            action_used=follow_up.action_used,
        )
    return EnemyAutoTurnResult(
        state=follow_up.state,
        enemy=moved_enemy,
        target=follow_up.target,
        message=f"{movement_message} {follow_up.message}",
        movement_path=movement_path,
        moved_enemy=moved_enemy,
        attack_roll=follow_up.attack_roll,
        attack_resolution=follow_up.attack_resolution,
        damage=follow_up.damage,
        updated_target=follow_up.updated_target,
        action_used=follow_up.action_used,
    )


def _actor_for_target(state: CombatState, target: CombatTarget) -> Actor:
    for actor in state.actors:
        if str(actor.id) == target.id:
            return actor
    raise ValueError(f"Unknown target actor: {target.id}.")


def _actor_for_id(state: CombatState, actor_id) -> Actor:
    for actor in state.actors:
        if actor.id == actor_id:
            return actor
    raise ValueError(f"Unknown actor: {actor_id}.")


def _select_enemy_target(enemy: Actor, targets: tuple[CombatTarget, ...]) -> CombatTarget:
    return min(
        targets,
        key=lambda target: (
            max(abs(enemy.position.col - target.position.col), abs(enemy.position.row - target.position.row)),
            target.position.col,
            target.position.row,
            target.id,
        ),
    )


def _best_enemy_movement_path(board: BoardState, state: CombatState, enemy: Actor) -> PathResult | None:
    movement = movement_range(board, enemy, state.actors)
    opponents = tuple(
        actor for actor in state.actors if actor.faction != enemy.faction and not actor.is_defeated()
    )
    best_path: PathResult | None = None
    best_key: tuple[int, int, int, int, str] | None = None
    for destination in movement.reachable_tiles:
        if destination == enemy.position:
            continue
        candidate_enemy = replace(enemy, position=destination)
        candidate_actors = tuple(candidate_enemy if actor.id == enemy.id else actor for actor in state.actors)
        candidate_targets = legal_melee_targets(board, candidate_enemy, candidate_actors)
        can_attack_after_move = 0 if candidate_targets else 1
        distance_to_opponent = min(
            (
                max(abs(destination.col - opponent.position.col), abs(destination.row - opponent.position.row))
                for opponent in opponents
            ),
            default=999,
        )
        path = find_path(board, enemy, state.actors, destination)
        if not path.valid:
            continue
        key = (can_attack_after_move, distance_to_opponent, path.cost_feet, destination.col, destination.row)
        if best_key is None or key < best_key:
            best_key = key
            best_path = path
    return best_path


def _turn_result_from_attack(result: EnemyAutoAttackResult) -> EnemyAutoTurnResult:
    return EnemyAutoTurnResult(
        state=result.state,
        enemy=result.enemy,
        target=result.target,
        message=result.message,
        attack_roll=result.attack_roll,
        attack_resolution=result.attack_resolution,
        damage=result.damage,
        updated_target=result.updated_target,
        action_used=result.action_used,
    )
