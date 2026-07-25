from __future__ import annotations

import random
from dataclasses import dataclass, replace

from dnd_board_game.actors import (
    Actor,
    Faction,
    can_spend_actor_resource,
    skill_roll_modifiers,
    spend_actor_resource,
)
from dnd_board_game.rules import (
    D20RollInput,
    D20RollRequest,
    D20RollResult,
    RollMode,
    SaveDamageOnSuccess,
    SavingThrowRequest,
    SavingThrowResult,
    resolve_d20_roll,
)
from dnd_board_game.world import BoardState, PathResult, find_path, movement_range

from .action_economy import ActionUse
from .attack_flow import AttackDeclaration, AttackResolution, AttackSource, legal_attack_targets, legal_melee_targets, resolve_attack
from .attack_positioning import AttackPositioning, attack_source_with_positioning, evaluate_attack_positioning
from .conditions import CombatCondition, attack_source_with_prone, condition_roll_request, has_condition, path_with_condition_cost
from .scene import SceneObject
from .stealth import is_hidden_from, resolve_search, reveal_actor
from .damage import (
    AppliedDamageResult,
    DamageComponentInput,
    DamageResult,
    apply_damage_result,
    resolve_damage,
    roll_damage_components,
)
from .session import (
    CombatState,
    movement_remaining,
    replace_actor,
    stand_up,
    use_attack_action,
    use_movement,
    use_turn_action,
)
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
    applied_damage: AppliedDamageResult | None = None
    updated_target: Actor | None = None
    action_used: bool = False
    positioning: AttackPositioning = AttackPositioning()
    source: AttackSource | None = None
    saving_throw_request: SavingThrowRequest | None = None
    saving_throw_result: SavingThrowResult | None = None
    base_damage: int | None = None
    base_damage_components: tuple[DamageComponentInput, ...] = ()


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
    applied_damage: AppliedDamageResult | None = None
    updated_target: Actor | None = None
    action_used: bool = False
    positioning: AttackPositioning = AttackPositioning()
    source: AttackSource | None = None
    saving_throw_request: SavingThrowRequest | None = None
    saving_throw_result: SavingThrowResult | None = None
    base_damage: int | None = None
    base_damage_components: tuple[DamageComponentInput, ...] = ()


@dataclass(frozen=True, slots=True)
class EnemyTurnPlan:
    state: CombatState
    enemy: Actor
    target: CombatTarget | None
    message: str
    movement_path: PathResult | None = None
    moved_enemy: Actor | None = None
    action_used: bool = False


def resolve_enemy_auto_attack(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    rng: random.Random,
    scene_objects: tuple[SceneObject, ...] = (),
    *,
    maximum_attacks: int | None = None,
) -> EnemyAutoAttackResult:
    if source.resource_pool_id is not None and not can_spend_actor_resource(
        enemy,
        source.resource_pool_id,
        source.resource_cost,
    ):
        return EnemyAutoAttackResult(
            state,
            enemy,
            None,
            f"{source.name} nie jest jeszcze dostępne — oczekuje na recharge.",
            action_used=False,
            source=source,
        )
    action_result = use_attack_action(state, enemy, maximum_attacks=maximum_attacks)
    if not action_result.accepted:
        return EnemyAutoAttackResult(action_result.state, enemy, None, action_result.message, action_used=False)
    if source.resource_pool_id is not None:
        usage = spend_actor_resource(
            _actor_for_id(action_result.state, enemy.id),
            source.resource_pool_id,
            source.resource_cost,
        )
        action_result = replace(
            action_result,
            state=replace_actor(action_result.state, usage.actor_after),
        )
        enemy = usage.actor_after

    targets = legal_attack_targets(
        board,
        enemy,
        action_result.state.actors,
        source,
        action_result.state.hidden_states,
    )
    if not targets:
        return EnemyAutoAttackResult(
            action_result.state,
            enemy,
            None,
            f"{enemy.name} nie ma legalnego celu ataku i kończy akcję.",
            action_used=True,
        )

    target = _select_enemy_target(enemy, targets)
    target_actor = _actor_for_target(action_result.state, target)
    positioning = evaluate_attack_positioning(
        board,
        enemy,
        target_actor,
        source,
        action_result.state.actors,
        scene_objects,
    )
    source = attack_source_with_positioning(source, positioning)
    source = attack_source_with_prone(
        source,
        action_result.state.condition_states,
        enemy,
        target_actor,
    )
    target = replace(target, ac=target.ac + positioning.cover_bonus)
    if source.save_ability is not None:
        dc = int(source.save_dc or enemy.spell_save_dc)
        if dc <= 0:
            raise ValueError(f"Atak {source.name} wymaga dodatniego ST rzutu obronnego.")
        base_damage_components = roll_damage_components(
            source.damage_components,
            lambda sides: rng.randint(1, sides),
        )
        base_damage = sum(component.amount for component in base_damage_components)
        saving_throw_request = SavingThrowRequest(
            ability=source.save_ability,
            dc=dc,
            source_label=source.name,
            dc_source_label=f"ST efektu: {source.name}",
            damage_on_success=SaveDamageOnSuccess(source.save_damage_on_success),
        )
        updated_state = replace(
            action_result.state,
            hidden_states=reveal_actor(action_result.state.hidden_states, str(enemy.id)),
        )
        return EnemyAutoAttackResult(
            state=updated_state,
            enemy=enemy,
            target=target,
            message=(
                f"{enemy.name} używa {source.name} przeciwko {target.name}. "
                f"Cel wykonuje {source.save_ability} save przeciw ST {dc}."
            ),
            action_used=True,
            positioning=positioning,
            source=source,
            saving_throw_request=saving_throw_request,
            base_damage=base_damage,
            base_damage_components=base_damage_components,
        )
    attack_roll = resolve_d20_roll(_roll_input_for_request(source.attack_roll_request, rng))
    declaration = AttackDeclaration(attacker=enemy, target=target, source=source)
    resolution = resolve_attack(declaration, attack_roll, ActionUse.ACTION_AVAILABLE)
    updated_state = action_result.state
    damage: DamageResult | None = None
    applied_damage: AppliedDamageResult | None = None
    updated_target: Actor | None = None

    if resolution.hit:
        damage = resolve_damage(
            roll_damage_components(
                source.damage_components,
                lambda sides: rng.randint(1, sides),
                critical=resolution.critical,
            )
        )
        applied_damage = apply_damage_result(
            target_actor,
            damage,
            critical=resolution.critical,
        )
        damage = applied_damage.damage
        updated_target = applied_damage.actor_after
        updated_state = replace_actor(action_result.state, updated_target)
        defeated_text = " Cel zostaje pokonany." if applied_damage.defeated_by_damage else ""
        message = (
            f"{enemy.name} trafia {target.name}. Wynik ataku: {attack_roll.total}. "
            f"Obrażenia: {_damage_result_text(damage)}. "
            f"{target_actor.name}: HP {applied_damage.hp_before} -> {applied_damage.hp_after}.{defeated_text}"
        )
    else:
        message = f"{enemy.name} pudłuje przeciwko {target.name}. Wynik ataku: {attack_roll.total}."

    updated_state = replace(
        updated_state,
        hidden_states=reveal_actor(updated_state.hidden_states, str(enemy.id)),
    )
    return EnemyAutoAttackResult(
        state=updated_state,
        enemy=enemy,
        target=target,
        message=message,
        attack_roll=attack_roll,
        attack_resolution=resolution,
        damage=damage,
        applied_damage=applied_damage,
        updated_target=updated_target,
        action_used=True,
        positioning=positioning,
        source=source,
    )


def _roll_input_for_request(request, rng: random.Random) -> D20RollInput:
    first = rng.randint(1, 20)
    if request.mode == RollMode.NORMAL:
        return D20RollInput(request, first)
    return D20RollInput(request, first, rng.randint(1, 20))


def resolve_enemy_auto_turn(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    rng: random.Random,
    scene_objects: tuple[SceneObject, ...] = (),
    *,
    maximum_attacks: int | None = None,
) -> EnemyAutoTurnResult:
    plan = plan_enemy_turn(board, state, enemy, source)
    stood_up = (
        has_condition(state.condition_states, str(enemy.id), CombatCondition.PRONE)
        and not has_condition(plan.state.condition_states, str(enemy.id), CombatCondition.PRONE)
    )
    movement_message = (
        f"{enemy.name} wstaje, wydając połowę szybkości. "
        if stood_up
        else ""
    )
    if plan.target is None:
        if plan.movement_path is not None:
            follow_up = resolve_enemy_auto_attack(
                board,
                plan.state,
                plan.enemy,
                source,
                rng,
                scene_objects,
                maximum_attacks=maximum_attacks,
            )
            return EnemyAutoTurnResult(
                follow_up.state,
                plan.enemy,
                None,
                plan.message,
                movement_path=plan.movement_path,
                moved_enemy=plan.moved_enemy,
                action_used=follow_up.action_used,
                positioning=follow_up.positioning,
            )
        hidden_opponents = tuple(
            actor
            for actor in plan.state.actors
            if actor.faction not in {enemy.faction, Faction.NEUTRAL}
            and not actor.is_defeated()
            and is_hidden_from(plan.state.hidden_states, str(actor.id), str(enemy.id))
        )
        if hidden_opponents and not plan.action_used:
            action = use_turn_action(plan.state)
            perception = resolve_d20_roll(
                D20RollInput(
                    condition_roll_request(
                        D20RollRequest(modifiers=skill_roll_modifiers(enemy, "perception")),
                        action.state.condition_states,
                        enemy,
                        ability_check=True,
                    ),
                    rng.randint(1, 20),
                )
            )
            search = resolve_search(action.state.hidden_states, enemy, perception.total)
            found_names = ", ".join(
                actor.name
                for actor in hidden_opponents
                if str(actor.id) in search.found_actor_ids
            )
            message = (
                f"{enemy.name} używa Search ({perception.total}) i odnajduje: {found_names}."
                if found_names
                else f"{enemy.name} używa Search ({perception.total}), ale nikogo nie odnajduje."
            )
            return EnemyAutoTurnResult(
                replace(action.state, hidden_states=search.hidden_states),
                enemy,
                None,
                message,
                action_used=action.accepted,
            )
        return EnemyAutoTurnResult(
            plan.state,
            plan.enemy,
            None,
            plan.message,
            movement_path=plan.movement_path,
            moved_enemy=plan.moved_enemy,
            action_used=plan.action_used,
        )
    attack = resolve_enemy_auto_attack(
        board,
        plan.state,
        plan.enemy,
        source,
        rng,
        scene_objects,
        maximum_attacks=maximum_attacks,
    )
    if plan.movement_path is None:
        return _turn_result_from_attack(attack)
    if attack.target is None:
        return EnemyAutoTurnResult(
            attack.state,
            plan.enemy,
            None,
            f"{movement_message}{_enemy_movement_message(enemy, plan.movement_path)} Po ruchu nadal nie ma legalnego celu ataku.",
            movement_path=plan.movement_path,
            moved_enemy=plan.moved_enemy,
            action_used=attack.action_used,
        )
    return EnemyAutoTurnResult(
        state=attack.state,
        enemy=plan.enemy,
        target=attack.target,
        message=f"{movement_message}{_enemy_movement_message(enemy, plan.movement_path)} {attack.message}",
        movement_path=plan.movement_path,
        moved_enemy=plan.moved_enemy,
        attack_roll=attack.attack_roll,
        attack_resolution=attack.attack_resolution,
        damage=attack.damage,
        applied_damage=attack.applied_damage,
        updated_target=attack.updated_target,
        action_used=attack.action_used,
        positioning=attack.positioning,
        source=attack.source,
        saving_throw_request=attack.saving_throw_request,
        saving_throw_result=attack.saving_throw_result,
        base_damage=attack.base_damage,
    )


def plan_enemy_turn(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource | None = None,
) -> EnemyTurnPlan:
    opening_message = ""
    if has_condition(state.condition_states, str(enemy.id), CombatCondition.PRONE):
        standing = stand_up(state, enemy)
        if standing.accepted:
            state = standing.state
            enemy = _actor_for_id(state, enemy.id)
            opening_message = f"{standing.message} "
    targets = (
        legal_attack_targets(board, enemy, state.actors, source, state.hidden_states)
        if source is not None
        else legal_melee_targets(board, enemy, state.actors, state.hidden_states)
    )
    if targets:
        target = _select_enemy_target(enemy, targets)
        return EnemyTurnPlan(state, enemy, target, f"{opening_message}{enemy.name} atakuje {target.name}.")

    movement_path = _best_enemy_movement_path(board, state, enemy, source)
    if movement_path is not None and movement_path.valid and movement_path.destination != enemy.position:
        movement = use_movement(state, enemy, movement_path)
        moved_state = movement.state
        moved_enemy = _actor_for_id(moved_state, enemy.id)
        moved_targets = (
            legal_attack_targets(
                board, moved_enemy, moved_state.actors, source, moved_state.hidden_states
            )
            if source is not None
            else legal_melee_targets(
                board, moved_enemy, moved_state.actors, moved_state.hidden_states
            )
        )
        target = _select_enemy_target(moved_enemy, moved_targets) if moved_targets else None
        message = f"{opening_message}{_enemy_movement_message(enemy, movement_path)}"
        if target is not None:
            message = f"{message} Po ruchu atakuje {target.name}."
        else:
            message = f"{message} Po ruchu nadal nie ma legalnego celu ataku."
        return EnemyTurnPlan(
            moved_state,
            moved_enemy,
            target,
            message,
            movement_path=movement_path,
            moved_enemy=moved_enemy,
        )

    has_hidden_opponent = any(
        actor.faction not in {enemy.faction, Faction.NEUTRAL}
        and not actor.is_defeated()
        and is_hidden_from(state.hidden_states, str(actor.id), str(enemy.id))
        for actor in state.actors
    )
    if has_hidden_opponent:
        return EnemyTurnPlan(
            state,
            enemy,
            None,
            f"{opening_message}{enemy.name} nie widzi celu i zamierza użyć Search.",
            action_used=False,
        )
    action_result = use_turn_action(state)
    return EnemyTurnPlan(
        action_result.state,
        enemy,
        None,
        f"{opening_message}{enemy.name} nie ma legalnego celu ani dostępnego ruchu i kończy akcję.",
        action_used=action_result.accepted,
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


def _best_enemy_movement_path(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource | None = None,
) -> PathResult | None:
    budget = movement_remaining(state, enemy)
    movement_actor = replace(enemy, speed_feet=budget)
    movement = movement_range(board, movement_actor, state.actors)
    opponents = tuple(
        actor
        for actor in state.actors
        if actor.faction not in {enemy.faction, Faction.NEUTRAL}
        and not actor.is_defeated()
        and not is_hidden_from(state.hidden_states, str(actor.id), str(enemy.id))
    )
    if not opponents:
        return None
    best_path: PathResult | None = None
    best_key: tuple[int, int, int, int, str] | None = None
    for destination in movement.reachable_tiles:
        if destination == enemy.position:
            continue
        candidate_enemy = replace(enemy, position=destination)
        candidate_actors = tuple(candidate_enemy if actor.id == enemy.id else actor for actor in state.actors)
        candidate_targets = (
            legal_attack_targets(
                board,
                candidate_enemy,
                candidate_actors,
                source,
                state.hidden_states,
            )
            if source is not None
            else legal_melee_targets(
                board,
                candidate_enemy,
                candidate_actors,
                state.hidden_states,
            )
        )
        can_attack_after_move = 0 if candidate_targets else 1
        distance_to_opponent = min(
            (
                max(abs(destination.col - opponent.position.col), abs(destination.row - opponent.position.row))
                for opponent in opponents
            ),
            default=999,
        )
        path = find_path(board, movement_actor, state.actors, destination)
        path = path_with_condition_cost(
            path,
            state.condition_states,
            str(enemy.id),
            movement_budget_feet=budget,
        )
        if not path.valid:
            continue
        key = (can_attack_after_move, path.cost_feet, distance_to_opponent, destination.col, destination.row)
        if best_key is None or key < best_key:
            best_key = key
            best_path = path
    return best_path


def _enemy_movement_message(enemy: Actor, movement_path: PathResult) -> str:
    return f"{enemy.name} rusza się na {movement_path.destination.as_tuple()}."


def _turn_result_from_attack(result: EnemyAutoAttackResult) -> EnemyAutoTurnResult:
    return EnemyAutoTurnResult(
        state=result.state,
        enemy=result.enemy,
        target=result.target,
        message=result.message,
        attack_roll=result.attack_roll,
        attack_resolution=result.attack_resolution,
        damage=result.damage,
        applied_damage=result.applied_damage,
        updated_target=result.updated_target,
        action_used=result.action_used,
        positioning=result.positioning,
        source=result.source,
        saving_throw_request=result.saving_throw_request,
        saving_throw_result=result.saving_throw_result,
        base_damage=result.base_damage,
        base_damage_components=result.base_damage_components,
    )


def _damage_result_text(damage: DamageResult) -> str:
    parts = []
    for component in damage.resolved_components:
        amount = (
            f"{component.amount_before} -> {component.amount_applied}"
            if component.changed
            else str(component.amount_applied)
        )
        parts.append(f"{amount} {component.damage_type.value}")
    return ", ".join(parts) + f"; razem {damage.total_applied}"
