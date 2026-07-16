from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import D20RollRequest, RollMode, RollModifier, RollModifierType
from dnd_board_game.world import MovementRangeResult, PathResult

from .attack_flow import AttackSource


class CombatCondition(StrEnum):
    PRONE = "prone"
    GRAPPLED = "grappled"


@dataclass(frozen=True, slots=True)
class ConditionState:
    actor_id: str
    condition: CombatCondition
    source_actor_id: str | None = None

    def __post_init__(self) -> None:
        if not self.actor_id:
            raise ValueError("Condition actor id cannot be empty.")
        if self.condition == CombatCondition.GRAPPLED and not self.source_actor_id:
            raise ValueError("Grappled condition requires a source actor id.")
        if self.source_actor_id == self.actor_id:
            raise ValueError("An actor cannot be the source of its own condition.")


def has_condition(
    states: Sequence[ConditionState],
    actor_id: str,
    condition: CombatCondition,
) -> bool:
    return any(state.actor_id == actor_id and state.condition == condition for state in states)


def add_condition(
    states: Sequence[ConditionState],
    actor_id: str,
    condition: CombatCondition,
    *,
    source_actor_id: str | None = None,
) -> tuple[ConditionState, ...]:
    if any(
        state.actor_id == actor_id
        and state.condition == condition
        and state.source_actor_id == source_actor_id
        for state in states
    ):
        return tuple(states)
    return (*states, ConditionState(actor_id, condition, source_actor_id))


def remove_condition(
    states: Sequence[ConditionState],
    actor_id: str,
    condition: CombatCondition,
) -> tuple[ConditionState, ...]:
    return tuple(
        state
        for state in states
        if not (state.actor_id == actor_id and state.condition == condition)
    )


def grappled_by(
    states: Sequence[ConditionState],
    actor_id: str,
) -> str | None:
    state = next(
        (
            state
            for state in states
            if state.actor_id == actor_id
            and state.condition == CombatCondition.GRAPPLED
        ),
        None,
    )
    return state.source_actor_id if state is not None else None


def grappled_actor_ids(
    states: Sequence[ConditionState],
    source_actor_id: str,
) -> tuple[str, ...]:
    return tuple(
        state.actor_id
        for state in states
        if state.condition == CombatCondition.GRAPPLED
        and state.source_actor_id == source_actor_id
    )


def remove_grapple(
    states: Sequence[ConditionState],
    actor_id: str,
    *,
    source_actor_id: str | None = None,
) -> tuple[ConditionState, ...]:
    return tuple(
        state
        for state in states
        if not (
            state.actor_id == actor_id
            and state.condition == CombatCondition.GRAPPLED
            and (source_actor_id is None or state.source_actor_id == source_actor_id)
        )
    )


def normalize_grapple_conditions(
    states: Sequence[ConditionState],
    actors: Sequence[Actor],
) -> tuple[ConditionState, ...]:
    """Remove grapples whose source/target cannot maintain a 5 ft hold."""

    actors_by_id = {str(actor.id): actor for actor in actors}
    normalized: list[ConditionState] = []
    for state in states:
        if state.condition != CombatCondition.GRAPPLED:
            normalized.append(state)
            continue
        target = actors_by_id.get(state.actor_id)
        source = actors_by_id.get(state.source_actor_id or "")
        if target is None or source is None or target.is_defeated() or source.is_defeated():
            continue
        distance = max(
            abs(source.position.col - target.position.col),
            abs(source.position.row - target.position.row),
        )
        if distance <= 1:
            normalized.append(state)
    return tuple(normalized)


def standing_movement_cost(actor: Actor) -> int:
    return actor.speed_feet // 2


def path_with_condition_cost(
    path: PathResult,
    states: Sequence[ConditionState],
    actor_id: str,
    *,
    movement_budget_feet: int | None = None,
) -> PathResult:
    cost = path.cost_feet
    if (
        path.valid
        and path.destination != path.origin
        and has_condition(states, actor_id, CombatCondition.GRAPPLED)
    ):
        return replace(path, valid=False)
    if path.valid and has_condition(states, actor_id, CombatCondition.PRONE):
        cost += _base_path_distance(path.path)
    valid = path.valid and (
        movement_budget_feet is None or cost <= movement_budget_feet
    )
    return replace(path, cost_feet=cost, valid=valid)


def effective_movement_speed(
    actor: Actor,
    states: Sequence[ConditionState],
) -> int:
    if has_condition(states, str(actor.id), CombatCondition.GRAPPLED):
        return 0
    if grappled_actor_ids(states, str(actor.id)):
        return actor.speed_feet // 2
    return actor.speed_feet


def movement_range_with_condition_cost(
    movement: MovementRangeResult,
    states: Sequence[ConditionState],
    actor_id: str,
    *,
    movement_budget_feet: int,
) -> MovementRangeResult:
    costs: dict = {}
    paths: dict = {}
    for tile, path_positions in movement.paths_by_tile.items():
        path = PathResult(
            movement.origin,
            tile,
            path_positions,
            movement.costs_by_tile[tile],
            tile in movement.reachable_tiles,
        )
        adjusted = path_with_condition_cost(
            path,
            states,
            actor_id,
            movement_budget_feet=movement_budget_feet,
        )
        if adjusted.valid:
            costs[tile] = adjusted.cost_feet
            paths[tile] = adjusted.path
    return MovementRangeResult(
        origin=movement.origin,
        reachable_tiles=frozenset(costs),
        costs_by_tile=costs,
        paths_by_tile=paths,
    )


def attack_source_with_prone(
    source: AttackSource,
    states: Sequence[ConditionState],
    attacker: Actor,
    target: Actor,
) -> AttackSource:
    if source.save_ability is not None or source.area is not None:
        return source
    attacker_prone = has_condition(states, str(attacker.id), CombatCondition.PRONE)
    target_prone = has_condition(states, str(target.id), CombatCondition.PRONE)
    target_within_five_feet = max(
        abs(attacker.position.col - target.position.col),
        abs(attacker.position.row - target.position.row),
    ) <= 1
    advantage = target_prone and target_within_five_feet
    disadvantage = attacker_prone or (target_prone and not target_within_five_feet)
    if not advantage and not disadvantage:
        return source

    request = source.attack_roll_request
    mode = _mode_with_factors(request.mode, advantage=advantage, disadvantage=disadvantage)
    modifiers = list(request.modifiers)
    if attacker_prone:
        modifiers.append(_factor("Atak w pozycji powalonej", "prone_attacker"))
    if target_prone:
        modifiers.append(
            _factor(
                "Powalony cel w zasięgu 5 ft" if target_within_five_feet else "Powalony cel dalej niż 5 ft",
                "prone_target_close" if target_within_five_feet else "prone_target_far",
            )
        )
    return replace(
        source,
        attack_roll_request=D20RollRequest(mode=mode, modifiers=tuple(modifiers)),
    )


def _base_path_distance(path: Sequence) -> int:
    distance = 0
    diagonal_parity = 0
    for origin, destination in zip(path, path[1:]):
        diagonal = origin.col != destination.col and origin.row != destination.row
        if diagonal:
            distance += 10 if diagonal_parity else 5
            diagonal_parity = 1 - diagonal_parity
        else:
            distance += 5
    return distance


def _mode_with_factors(
    current: RollMode,
    *,
    advantage: bool,
    disadvantage: bool,
) -> RollMode:
    if advantage and disadvantage:
        return RollMode.NORMAL
    if advantage:
        return RollMode.NORMAL if current == RollMode.DISADVANTAGE else RollMode.ADVANTAGE
    if disadvantage:
        return RollMode.NORMAL if current == RollMode.ADVANTAGE else RollMode.DISADVANTAGE
    return current


def _factor(label: str, stacking_key: str) -> RollModifier:
    return RollModifier(
        label,
        0,
        RollModifierType.SITUATIONAL,
        stacking_key=stacking_key,
    )
