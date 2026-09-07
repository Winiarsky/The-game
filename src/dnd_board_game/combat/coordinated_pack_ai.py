from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import Mapping, Sequence

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.world import (
    BoardState,
    Coordinate,
    PathResult,
    line_of_sight_clear,
    movement_range,
)

from .attack_flow import AttackKind, AttackSource, CombatTarget, legal_attack_targets
from .enemy_ai import EnemyTurnPlan, plan_enemy_turn
from .session import CombatState, movement_remaining, use_dash, use_movement, use_turn_action
from .stealth import actors_visible_for_pathfinding, is_hidden_from


LEADER_ROLE = "leader"


def plan_coordinated_pack_turn(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    sources: Sequence[AttackSource],
    *,
    role_id: str,
    actor_roles: Mapping[str, str],
    escape_positions: tuple[Coordinate, ...] = (),
) -> EnemyTurnPlan:
    """Plan one Hungry Shadows turn without rolling dice or mutating external state."""
    if not sources:
        raise ValueError(f"Aktor {enemy.name} nie ma zdefiniowanego ataku.")
    leader_ids = {
        actor_id for actor_id, role in actor_roles.items() if role == LEADER_ROLE
    }
    # The one-player fixture intentionally has no leader and keeps its simpler AI.
    if not leader_ids:
        return plan_enemy_turn(board, state, enemy, sources[0])

    living_enemies = tuple(
        actor
        for actor in state.actors
        if actor.faction == Faction.ENEMY
        and actor.can_take_combat_turn()
        and str(actor.id) not in state.enemy_ai.escaped_actor_ids
    )
    living_leaders = tuple(actor for actor in living_enemies if str(actor.id) in leader_ids)
    living_followers = tuple(actor for actor in living_enemies if str(actor.id) not in leader_ids)
    retreat_reason = (
        "leader_lost" if not living_leaders else "followers_lost" if not living_followers else ""
    )
    if retreat_reason:
        return _plan_retreat(
            board,
            state,
            enemy,
            sources,
            escape_positions,
            retreat_reason=retreat_reason,
        )
    if role_id == LEADER_ROLE:
        return _plan_leader(board, state, enemy, sources, living_followers)
    return _plan_follower(board, state, enemy, sources[0], living_followers, role_id=role_id)


def _plan_leader(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    sources: Sequence[AttackSource],
    followers: Sequence[Actor],
) -> EnemyTurnPlan:
    melee = next((source for source in sources if source.attack_kind == AttackKind.MELEE), None)
    ranged = next((source for source in sources if source.attack_kind == AttackKind.RANGED), None)
    if melee is None or ranged is None:
        return plan_enemy_turn(board, state, enemy, sources[0])
    opponents = _visible_opponents(state, enemy)
    adjacent = tuple(actor for actor in opponents if _tile_distance(enemy.position, actor.position) <= 1)
    if adjacent:
        target_actor = _injury_tiebreak(state, enemy, adjacent)
        target = _target_by_id(board, state, enemy, melee, str(target_actor.id))
        if target is not None:
            return EnemyTurnPlan(
                state=state,
                enemy=enemy,
                target=target,
                message=f"{enemy.name} dopada {target.name} i atakuje w zwarciu.",
                intent="leader_melee",
                source_id=melee.id,
                life_drain=True,
            )

    legal_now = legal_attack_targets(board, enemy, state.actors, ranged, state.hidden_states)
    if legal_now:
        target = _pack_target(state, enemy, legal_now, followers)
        heal_target = _most_wounded(board, enemy, followers)
        healing = (
            f" Po ataku spróbuje odnowić siły {heal_target.name}."
            if heal_target is not None
            else ""
        )
        return EnemyTurnPlan(
            state=state,
            enemy=enemy,
            target=target,
            message=(
                f"{enemy.name} utrzymuje dystans i używa {ranged.name} przeciw {target.name}."
                f"{healing}"
            ),
            intent="leader_ranged",
            source_id=ranged.id,
            pack_heal_target_id=str(heal_target.id) if heal_target is not None else None,
        )

    shot_options: list[tuple[int, int, Coordinate, CombatTarget]] = []
    reachable = _reachable(state, board, enemy)
    for position in reachable.reachable_tiles:
        if position == enemy.position:
            continue
        moved_enemy, actors = _actors_with_position(state, enemy, position)
        legal = legal_attack_targets(board, moved_enemy, actors, ranged, state.hidden_states)
        if not legal:
            continue
        target = _pack_target(state, moved_enemy, legal, followers)
        shot_options.append(
            (
                reachable.costs_by_tile[position],
                -_tile_distance(position, target.position),
                position,
                target,
            )
        )
    if shot_options:
        _, _, destination, target = min(shot_options)
        moved_state, moved_enemy, path = _move_to(state, board, enemy, destination)
        return EnemyTurnPlan(
            state=moved_state,
            enemy=moved_enemy,
            target=target,
            message=(
                f"{enemy.name} podchodzi tylko tyle, ile trzeba, na {destination.as_tuple()} "
                f"i używa {ranged.name} przeciw {target.name}."
            ),
            movement_path=path,
            moved_enemy=moved_enemy,
            intent="leader_ranged",
            source_id=ranged.id,
        )

    preferred = _pack_actor_target(state, enemy, opponents, followers)
    if preferred is None:
        action = use_turn_action(state)
        return EnemyTurnPlan(
            state=action.state,
            enemy=enemy,
            target=None,
            message=f"{enemy.name} nie widzi żadnego celu i nasłuchuje.",
            action_used=action.accepted,
            intent="cornered",
            source_id=ranged.id,
        )
    return _dash_toward(board, state, enemy, preferred, ranged, "leader_advance")


def _plan_follower(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    followers: Sequence[Actor],
    *,
    role_id: str = "skirmisher",
) -> EnemyTurnPlan:
    opponents = _visible_opponents(state, enemy)
    uses_flank = role_id in {"flanker", "harrier"}
    target_actor = (
        _flank_actor_target(state, enemy, opponents, followers)
        if uses_flank else _pack_actor_target(state, enemy, opponents, followers)
    )
    if target_actor is None:
        action = use_turn_action(state)
        return EnemyTurnPlan(
            action.state,
            enemy,
            None,
            f"{enemy.name} nie widzi żadnego celu i nasłuchuje.",
            action_used=action.accepted,
            intent="cornered",
            source_id=source.id,
        )

    legal_now = _target_by_id(board, state, enemy, source, str(target_actor.id))
    if legal_now is not None:
        bonus = _support_count(followers, enemy, target_actor.position)
        return EnemyTurnPlan(
            state,
            enemy,
            legal_now,
            _follower_attack_message(enemy, legal_now, bonus),
            intent="pack_attack",
            source_id=source.id,
            pack_attack_bonus=bonus,
        )

    reachable = _reachable(state, board, enemy)
    side = (-1 if enemy.position.col < target_actor.position.col else 1) if uses_flank else 0
    attack_tiles: list[tuple[int, int, int, Coordinate, CombatTarget]] = []
    for position in reachable.reachable_tiles:
        if position == enemy.position:
            continue
        moved_enemy, actors = _actors_with_position(state, enemy, position)
        target = next(
            (
                candidate
                for candidate in legal_attack_targets(
                    board, moved_enemy, actors, source, state.hidden_states
                )
                if candidate.id == str(target_actor.id)
            ),
            None,
        )
        if target is None:
            continue
        flanking = int(_is_flanking(position, target_actor.position, followers, enemy))
        opposite_side = int(side != 0 and (position.col - target_actor.position.col) * side < 0)
        attack_tiles.append((-flanking, opposite_side, reachable.costs_by_tile[position], position, target))
    if attack_tiles:
        _, _, _, destination, target = min(attack_tiles)
        moved_state, moved_enemy, path = _move_to(state, board, enemy, destination)
        moved_target = next(actor for actor in moved_state.actors if str(actor.id) == target.id)
        bonus = _support_count(followers, enemy, moved_target.position)
        return EnemyTurnPlan(
            moved_state,
            moved_enemy,
            target,
            (
                f"{enemy.name} {'obchodzi front ku' if uses_flank else 'skupia się na'} {target.name}, rusza na "
                f"{destination.as_tuple()} i atakuje. Premia stada: +{bonus}."
            ),
            movement_path=path,
            moved_enemy=moved_enemy,
            intent="pack_attack",
            source_id=source.id,
            pack_attack_bonus=bonus,
        )
    return _dash_toward(board, state, enemy, target_actor, source, "pack_advance", flank_side=side)


def _flank_actor_target(
    state: CombatState,
    enemy: Actor,
    opponents: Sequence[Actor],
    followers: Sequence[Actor],
) -> Actor | None:
    """Threaten a nearby exposed flank instead of reinforcing a crowded front."""
    if not opponents:
        return None
    adjacent = tuple(actor for actor in opponents if _tile_distance(enemy.position, actor.position) <= 1)
    if adjacent:
        return _injury_tiebreak(state, enemy, adjacent)
    nearest = min(_tile_distance(enemy.position, actor.position) for actor in opponents)
    candidates = tuple(actor for actor in opponents if _tile_distance(enemy.position, actor.position) <= nearest + 3)
    return min(candidates, key=lambda actor: (
        _adjacent_followers(followers, enemy, actor.position),
        sum(other.id != actor.id and _tile_distance(other.position, actor.position) <= 1 for other in opponents),
        _tile_distance(enemy.position, actor.position),
        actor.hp / max(1, actor.max_hp),
        _stable_tie(state, enemy, actor),
    ))


def _plan_retreat(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    sources: Sequence[AttackSource],
    escape_positions: tuple[Coordinate, ...],
    *,
    retreat_reason: str,
) -> EnemyTurnPlan:
    marker = f"coordinated_pack_retreat:{retreat_reason}"
    first_notice = marker not in state.enemy_ai.used_morale_events
    if first_notice:
        state = replace(
            state,
            enemy_ai=replace(
                state.enemy_ai,
                used_morale_events=(*state.enemy_ai.used_morale_events, marker),
            ),
        )
        enemy = next(actor for actor in state.actors if actor.id == enemy.id)
    notice = (
        " Stado traci oparcie i zmienia taktykę: pozostałe Cienie uciekają do podświetlonych wyjść."
        if first_notice
        else ""
    )
    if not escape_positions:
        return _cornered_plan(board, state, enemy, sources, notice)
    dashed = use_dash(state, enemy)
    planning_state = dashed.state if dashed.accepted else state
    reachable = _reachable(planning_state, board, enemy)
    reachable_exits = tuple(position for position in escape_positions if position in reachable.reachable_tiles)
    escape_target = min(
        escape_positions,
        key=lambda position: (_tile_distance(enemy.position, position), position.col, position.row),
    )
    if reachable_exits:
        destination = min(
            reachable_exits,
            key=lambda position: (reachable.costs_by_tile[position], position.col, position.row),
        )
    else:
        current_distance = min(_tile_distance(enemy.position, position) for position in escape_positions)
        progressing = tuple(
            position
            for position in reachable.reachable_tiles
            if position != enemy.position
            and min(_tile_distance(position, exit_) for exit_ in escape_positions) < current_distance
        )
        if not progressing:
            return _cornered_plan(board, state, enemy, sources, notice, escape_target)
        destination = min(
            progressing,
            key=lambda position: (
                min(_tile_distance(position, exit_) for exit_ in escape_positions),
                reachable.costs_by_tile[position],
                position.col,
                position.row,
            ),
        )
        escape_target = min(
            escape_positions,
            key=lambda position: (_tile_distance(destination, position), position.col, position.row),
        )
    moved_state, moved_enemy, path = _move_to(planning_state, board, enemy, destination)
    escaped = destination in escape_positions
    return EnemyTurnPlan(
        moved_state,
        moved_enemy,
        None,
        (
            f"{enemy.name} ucieka na {destination.as_tuple()}"
            f"{' i opuszcza planszę' if escaped else ''}.{notice}"
        ),
        movement_path=path,
        moved_enemy=moved_enemy,
        action_used=dashed.accepted,
        intent="flee",
        escaped=escaped,
        source_id=sources[0].id,
        escape_target=escape_target,
    )


def _cornered_plan(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    sources: Sequence[AttackSource],
    notice: str,
    escape_target: Coordinate | None = None,
) -> EnemyTurnPlan:
    for source in sources:
        legal = legal_attack_targets(board, enemy, state.actors, source, state.hidden_states)
        if legal:
            target = min(legal, key=lambda item: (_tile_distance(enemy.position, item.position), item.id))
            return EnemyTurnPlan(
                state,
                enemy,
                target,
                f"{enemy.name} nie ma drogi ucieczki i atakuje {target.name}.{notice}",
                intent="cornered",
                source_id=source.id,
                escape_target=escape_target,
            )
    action = use_turn_action(state)
    return EnemyTurnPlan(
        action.state,
        enemy,
        None,
        f"{enemy.name} jest osaczony i nie może zrobić postępu.{notice}",
        action_used=action.accepted,
        intent="cornered",
        source_id=sources[0].id,
        escape_target=escape_target,
    )


def _dash_toward(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    target: Actor,
    source: AttackSource,
    intent: str,
    *,
    flank_side: int = 0,
) -> EnemyTurnPlan:
    dashed = use_dash(state, enemy)
    planning_state = dashed.state if dashed.accepted else state
    reachable = _reachable(planning_state, board, enemy)
    before = _tile_distance(enemy.position, target.position)
    progressing = tuple(
        position
        for position in reachable.reachable_tiles
        if position != enemy.position and _tile_distance(position, target.position) < before
    )
    if not progressing:
        return _cornered_plan(board, state, enemy, (source,), "")
    destination = min(
        progressing,
        key=lambda position: (
            _tile_distance(position, target.position)
            + (2 if flank_side and (position.col - target.position.col) * flank_side < 0 else 0),
            reachable.costs_by_tile[position],
            position.col,
            position.row,
        ),
    )
    moved_state, moved_enemy, path = _move_to(planning_state, board, enemy, destination)
    return EnemyTurnPlan(
        moved_state,
        moved_enemy,
        None,
        f"{enemy.name} {'obiega flankę ku' if flank_side else 'pędzi ku'} {target.name} na {destination.as_tuple()}.",
        movement_path=path,
        moved_enemy=moved_enemy,
        action_used=dashed.accepted,
        intent=intent,
        source_id=source.id,
    )


def _visible_opponents(state: CombatState, enemy: Actor) -> tuple[Actor, ...]:
    return tuple(
        actor
        for actor in state.actors
        if actor.faction not in {enemy.faction, Faction.NEUTRAL}
        and actor.can_take_combat_turn()
        and not is_hidden_from(state.hidden_states, str(actor.id), str(enemy.id))
    )


def _pack_actor_target(
    state: CombatState,
    enemy: Actor,
    opponents: Sequence[Actor],
    followers: Sequence[Actor],
) -> Actor | None:
    if not opponents:
        return None
    support = {
        str(actor.id): _adjacent_followers(followers, enemy, actor.position)
        for actor in opponents
    }
    maximum = max(support.values(), default=0)
    candidates = tuple(actor for actor in opponents if support[str(actor.id)] == maximum)
    nearest = min(_tile_distance(enemy.position, actor.position) for actor in candidates)
    candidates = tuple(actor for actor in candidates if _tile_distance(enemy.position, actor.position) == nearest)
    return _injury_tiebreak(state, enemy, candidates)


def _pack_target(
    state: CombatState,
    enemy: Actor,
    targets: Sequence[CombatTarget],
    followers: Sequence[Actor],
) -> CombatTarget:
    actors = {
        str(actor.id): actor for actor in state.actors if any(target.id == str(actor.id) for target in targets)
    }
    chosen = _pack_actor_target(state, enemy, tuple(actors.values()), followers)
    assert chosen is not None
    return next(target for target in targets if target.id == str(chosen.id))


def _injury_tiebreak(
    state: CombatState,
    enemy: Actor,
    actors: Sequence[Actor],
) -> Actor:
    worst_ratio = min(actor.hp / max(1, actor.max_hp) for actor in actors)
    candidates = tuple(actor for actor in actors if actor.hp / max(1, actor.max_hp) == worst_ratio)
    lowest_hp = min(actor.hp for actor in candidates)
    candidates = tuple(actor for actor in candidates if actor.hp == lowest_hp)
    return min(candidates, key=lambda actor: _stable_tie(state, enemy, actor))


def _stable_tie(state: CombatState, enemy: Actor, actor: Actor) -> str:
    raw = f"{state.enemy_ai.encounter_seed}:{state.round_number}:{enemy.id}:{actor.id}"
    return sha256(raw.encode("utf-8")).hexdigest()


def _adjacent_followers(
    followers: Sequence[Actor],
    deciding_actor: Actor,
    position: Coordinate,
) -> int:
    return sum(
        actor.id != deciding_actor.id
        and actor.can_take_combat_turn()
        and _tile_distance(actor.position, position) <= 1
        for actor in followers
    )


def _support_count(
    followers: Sequence[Actor],
    attacker: Actor,
    target_position: Coordinate,
) -> int:
    return sum(
        actor.id != attacker.id
        and actor.can_take_combat_turn()
        and _tile_distance(actor.position, target_position) <= 1
        for actor in followers
    )


def _most_wounded(
    board: BoardState,
    leader: Actor,
    followers: Sequence[Actor],
) -> Actor | None:
    damaged = tuple(
        actor
        for actor in followers
        if actor.can_take_combat_turn()
        and actor.hp < actor.max_hp
        and _tile_distance(leader.position, actor.position) <= 12
        and line_of_sight_clear(board, leader.position, actor.position)
    )
    return min(damaged, key=lambda actor: (-(actor.max_hp - actor.hp), actor.hp, str(actor.id)), default=None)


def _target_by_id(
    board: BoardState,
    state: CombatState,
    enemy: Actor,
    source: AttackSource,
    actor_id: str,
) -> CombatTarget | None:
    return next(
        (
            target
            for target in legal_attack_targets(
                board, enemy, state.actors, source, state.hidden_states
            )
            if target.id == actor_id
        ),
        None,
    )


def _reachable(state: CombatState, board: BoardState, enemy: Actor):
    budget = movement_remaining(state, enemy)
    moving = replace(enemy, speed_feet=budget)
    active = tuple(
        actor for actor in state.actors if str(actor.id) not in state.enemy_ai.escaped_actor_ids
    )
    return movement_range(
        board,
        moving,
        actors_visible_for_pathfinding(active, state.hidden_states, str(enemy.id)),
    )


def _move_to(
    state: CombatState,
    board: BoardState,
    enemy: Actor,
    destination: Coordinate,
) -> tuple[CombatState, Actor, PathResult]:
    reachable = _reachable(state, board, enemy)
    path = PathResult(
        enemy.position,
        destination,
        reachable.paths_by_tile[destination],
        reachable.costs_by_tile[destination],
        True,
    )
    moved = use_movement(state, enemy, path)
    if not moved.accepted:
        raise ValueError(moved.message)
    moved_enemy = next(actor for actor in moved.state.actors if actor.id == enemy.id)
    return moved.state, moved_enemy, path


def _actors_with_position(
    state: CombatState,
    enemy: Actor,
    position: Coordinate,
) -> tuple[Actor, tuple[Actor, ...]]:
    moved = replace(enemy, position=position)
    return moved, tuple(moved if actor.id == enemy.id else actor for actor in state.actors)


def _is_flanking(
    attacker_position: Coordinate,
    target_position: Coordinate,
    followers: Sequence[Actor],
    attacker: Actor,
) -> bool:
    attack_vector = (
        attacker_position.col - target_position.col,
        attacker_position.row - target_position.row,
    )
    return any(
        ally.id != attacker.id
        and ally.can_take_combat_turn()
        and _tile_distance(ally.position, target_position) <= 1
        and (
            ally.position.col - target_position.col,
            ally.position.row - target_position.row,
        )
        == (-attack_vector[0], -attack_vector[1])
        for ally in followers
    )


def _follower_attack_message(enemy: Actor, target: CombatTarget, bonus: int) -> str:
    return (
        f"{enemy.name} rzuca się na {target.name}. Premia stada: +{bonus} do ataku i obrażeń."
    )


def _tile_distance(first: Coordinate, second: Coordinate) -> int:
    return max(abs(first.col - second.col), abs(first.row - second.row))
