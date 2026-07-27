from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, Faction
from dnd_board_game.world import BoardState, Coordinate, line_of_sight_clear

from .scene import SceneObject
from .session import CombatState
from .spells import grid_distance_feet
from .stealth import is_hidden_from


class MagicMovementKind(StrEnum):
    TELEPORT = "teleport"
    PUSH = "push"
    PULL = "pull"


@dataclass(frozen=True, slots=True)
class MagicMovementDefinition:
    kind: MagicMovementKind
    distance_feet: int

    def __post_init__(self) -> None:
        if self.distance_feet < 5 or self.distance_feet % 5:
            raise ValueError(
                "Magic movement distance must be a positive multiple of 5."
            )


def legal_teleport_positions(
    board: BoardState,
    state: CombatState,
    caster: Actor,
    *,
    distance_feet: int,
    scene_objects: tuple[SceneObject, ...] = (),
) -> tuple[Coordinate, ...]:
    return tuple(
        position
        for row in range(board.dimensions.rows)
        for col in range(board.dimensions.cols)
        for position in (Coordinate(col, row),)
        if position != caster.position
        and grid_distance_feet(caster.position, position) <= distance_feet
        and line_of_sight_clear(board, caster.position, position)
        and _tile_available(
            board,
            state,
            position,
            moving_actor=caster,
            scene_objects=scene_objects,
        )
    )


def legal_forced_movement_targets(
    board: BoardState,
    state: CombatState,
    caster: Actor,
    *,
    kind: MagicMovementKind,
    range_feet: int,
    distance_feet: int,
    scene_objects: tuple[SceneObject, ...] = (),
) -> tuple[Actor, ...]:
    if kind not in {MagicMovementKind.PUSH, MagicMovementKind.PULL}:
        raise ValueError("Forced movement requires push or pull.")
    return tuple(
        actor
        for actor in state.actors
        if actor.faction not in {caster.faction, Faction.NEUTRAL}
        and not actor.is_defeated()
        and actor.position != caster.position
        and grid_distance_feet(caster.position, actor.position) <= range_feet
        and line_of_sight_clear(board, caster.position, actor.position)
        and not is_hidden_from(
            state.hidden_states,
            str(actor.id),
            str(caster.id),
        )
        and forced_movement_destination(
            board,
            state,
            caster,
            actor,
            kind=kind,
            distance_feet=distance_feet,
            scene_objects=scene_objects,
        )
        != actor.position
    )


def forced_movement_destination(
    board: BoardState,
    state: CombatState,
    caster: Actor,
    target: Actor,
    *,
    kind: MagicMovementKind,
    distance_feet: int,
    scene_objects: tuple[SceneObject, ...] = (),
) -> Coordinate:
    if kind not in {MagicMovementKind.PUSH, MagicMovementKind.PULL}:
        raise ValueError("Forced movement requires push or pull.")
    dc = _direction(target.position.col - caster.position.col)
    dr = _direction(target.position.row - caster.position.row)
    if kind == MagicMovementKind.PULL:
        dc, dr = -dc, -dr
    current = target.position
    for _ in range(distance_feet // 5):
        destination = Coordinate(current.col + dc, current.row + dr)
        if grid_distance_feet(target.position, destination) > distance_feet:
            break
        if not _step_available(
            board,
            state,
            current,
            destination,
            moving_actor=target,
            scene_objects=scene_objects,
        ):
            break
        current = destination
    return current


def move_actor_magically(
    state: CombatState,
    actor: Actor,
    destination: Coordinate,
) -> CombatState:
    from .session import replace_actor

    return replace_actor(state, replace(actor, position=destination))


def _step_available(
    board: BoardState,
    state: CombatState,
    origin: Coordinate,
    destination: Coordinate,
    *,
    moving_actor: Actor,
    scene_objects: tuple[SceneObject, ...],
) -> bool:
    if not _tile_available(
        board,
        state,
        destination,
        moving_actor=moving_actor,
        scene_objects=scene_objects,
    ):
        return False
    dc = destination.col - origin.col
    dr = destination.row - origin.row
    if abs(dc) + abs(dr) == 1:
        return not board.blocks_edge(origin, destination)
    side_a = Coordinate(destination.col, origin.row)
    side_b = Coordinate(origin.col, destination.row)
    return _orthogonal_side_open(board, origin, side_a) or _orthogonal_side_open(
        board,
        origin,
        side_b,
    )


def _tile_available(
    board: BoardState,
    state: CombatState,
    position: Coordinate,
    *,
    moving_actor: Actor,
    scene_objects: tuple[SceneObject, ...],
) -> bool:
    return bool(
        board.in_bounds(position)
        and not board.terrain_at(position).blocks_movement
        and not any(
            actor.id != moving_actor.id
            and not actor.is_defeated()
            and actor.position == position
            for actor in state.actors
        )
        and not any(
            obj.blocks_movement and position in obj.positions
            for obj in scene_objects
        )
    )


def _orthogonal_side_open(
    board: BoardState,
    origin: Coordinate,
    side: Coordinate,
) -> bool:
    return bool(
        board.in_bounds(side)
        and not board.terrain_at(side).blocks_movement
        and not board.blocks_edge(origin, side)
    )


def _direction(value: int) -> int:
    return 0 if value == 0 else 1 if value > 0 else -1
