from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from math import inf
from typing import Iterable, Sequence

from dnd_board_game.actors.models import Actor, is_ally_or_neutral

from .board_state import BoardState
from .coordinates import Coordinate

NORMAL_MOVE_COST_FEET = 5
DIFFICULT_MOVE_COST_FEET = 10


@dataclass(frozen=True, slots=True)
class MovementRangeResult:
    origin: Coordinate
    reachable_tiles: frozenset[Coordinate]
    costs_by_tile: dict[Coordinate, int]
    paths_by_tile: dict[Coordinate, tuple[Coordinate, ...]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PathResult:
    origin: Coordinate
    destination: Coordinate
    path: tuple[Coordinate, ...]
    cost_feet: int
    valid: bool


def neighbors(board: BoardState, coordinate: Coordinate, *, diagonal: bool = True) -> list[Coordinate]:
    if not board.in_bounds(coordinate):
        raise ValueError(f"Coordinate out of bounds: {coordinate}.")
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonal:
        offsets.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
    result: list[Coordinate] = []
    for dc, dr in offsets:
        candidate = Coordinate(coordinate.col + dc, coordinate.row + dr)
        if board.in_bounds(candidate):
            result.append(candidate)
    return sorted(result)


def movement_cost(
    board: BoardState,
    actor: Actor,
    actors: Sequence[Actor],
    destination: Coordinate,
) -> int | None:
    if not board.in_bounds(destination):
        return None
    terrain = board.terrain_at(destination)
    if terrain.blocks_movement:
        return None
    occupant = _occupant_at(actors, destination, ignore_actor=actor)
    if occupant is not None:
        if not is_ally_or_neutral(actor, occupant):
            return None
        return DIFFICULT_MOVE_COST_FEET
    if terrain.is_difficult:
        return DIFFICULT_MOVE_COST_FEET
    return NORMAL_MOVE_COST_FEET


def can_traverse(
    board: BoardState,
    actor: Actor,
    actors: Sequence[Actor],
    start: Coordinate,
    destination: Coordinate,
) -> bool:
    return _step_cost(board, actor, actors, start, destination, allow_occupied_destination=True) is not None


def movement_range(board: BoardState, actor: Actor, actors: Sequence[Actor]) -> MovementRangeResult:
    origin = actor.position
    if not board.in_bounds(origin):
        raise ValueError(f"Actor position out of bounds: {origin}.")

    costs: dict[Coordinate, int] = {origin: 0}
    paths: dict[Coordinate, tuple[Coordinate, ...]] = {origin: (origin,)}
    queue: list[tuple[int, Coordinate]] = [(0, origin)]

    while queue:
        current_cost, current = heapq.heappop(queue)
        if current_cost != costs[current]:
            continue
        for candidate in neighbors(board, current):
            step_cost = _step_cost(board, actor, actors, current, candidate, allow_occupied_destination=True)
            if step_cost is None:
                continue
            next_cost = current_cost + step_cost
            if next_cost > actor.speed_feet:
                continue
            if next_cost < costs.get(candidate, inf):
                costs[candidate] = next_cost
                paths[candidate] = (*paths[current], candidate)
                heapq.heappush(queue, (next_cost, candidate))

    reachable = {
        tile
        for tile, cost in costs.items()
        if cost <= actor.speed_feet and _can_end_movement(board, actor, actors, tile)
    }
    reachable.add(origin)
    return MovementRangeResult(
        origin=origin,
        reachable_tiles=frozenset(sorted(reachable)),
        costs_by_tile=dict(sorted(costs.items())),
        paths_by_tile={tile: paths[tile] for tile in sorted(paths)},
    )


def find_path(
    board: BoardState,
    actor: Actor,
    actors: Sequence[Actor],
    destination: Coordinate,
) -> PathResult:
    if not board.in_bounds(destination):
        return PathResult(actor.position, destination, (), 0, False)
    result = movement_range(board, actor, actors)
    path = result.paths_by_tile.get(destination)
    if path is None or destination not in result.reachable_tiles:
        return PathResult(actor.position, destination, path or (), result.costs_by_tile.get(destination, 0), False)
    return PathResult(actor.position, destination, path, result.costs_by_tile[destination], True)


def _step_cost(
    board: BoardState,
    actor: Actor,
    actors: Sequence[Actor],
    start: Coordinate,
    destination: Coordinate,
    *,
    allow_occupied_destination: bool,
) -> int | None:
    if not board.in_bounds(start) or not board.in_bounds(destination):
        return None
    if start == destination:
        return 0
    dc = abs(start.col - destination.col)
    dr = abs(start.row - destination.row)
    if max(dc, dr) != 1:
        return None
    if dc == 1 and dr == 1:
        if not _can_move_diagonal(board, actor, actors, start, destination):
            return None
    elif board.blocks_edge(start, destination):
        return None

    cost = movement_cost(board, actor, actors, destination)
    if cost is None:
        return None
    if not allow_occupied_destination and _occupant_at(actors, destination, ignore_actor=actor) is not None:
        return None
    return cost


def _can_move_diagonal(
    board: BoardState,
    actor: Actor,
    actors: Sequence[Actor],
    start: Coordinate,
    destination: Coordinate,
) -> bool:
    side_a = Coordinate(destination.col, start.row)
    side_b = Coordinate(start.col, destination.row)
    return _corner_side_open(board, actor, actors, start, side_a) or _corner_side_open(board, actor, actors, start, side_b)


def _corner_side_open(board: BoardState, actor: Actor, actors: Sequence[Actor], start: Coordinate, side: Coordinate) -> bool:
    if not board.in_bounds(side):
        return False
    if board.blocks_edge(start, side):
        return False
    terrain = board.terrain_at(side)
    if terrain.blocks_movement:
        return False
    occupant = _occupant_at(actors, side, ignore_actor=actor)
    if occupant is not None and not is_ally_or_neutral(actor, occupant):
        return False
    return True


def _can_end_movement(board: BoardState, actor: Actor, actors: Sequence[Actor], coordinate: Coordinate) -> bool:
    if not board.in_bounds(coordinate):
        return False
    if coordinate == actor.position:
        return True
    terrain = board.terrain_at(coordinate)
    if terrain.blocks_movement:
        return False
    return _occupant_at(actors, coordinate, ignore_actor=actor) is None


def _occupant_at(actors: Iterable[Actor], coordinate: Coordinate, *, ignore_actor: Actor) -> Actor | None:
    for actor in actors:
        if actor.id == ignore_actor.id:
            continue
        if actor.position == coordinate and not actor.is_defeated():
            return actor
    return None
