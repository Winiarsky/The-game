"""One-square diagonals and Parkour geometry for the charge combat profile."""
from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Sequence

from dnd_board_game.actors import Actor
from .board_state import BoardState
from .coordinates import Coordinate
from .movement import can_traverse, neighbors


@dataclass(frozen=True, slots=True)
class ChargePath:
    cells: tuple[Coordinate, ...]
    costs: tuple[int, ...]

    @property
    def cost(self) -> int:
        return sum(self.costs)

    def as_payload(self) -> dict[str, object]:
        return {"cells": [list(p) for p in self.cells], "costs": list(self.costs), "cost": self.cost}


def distance(a: Coordinate, b: Coordinate) -> int:
    return max(abs(a.col-b.col), abs(a.row-b.row))


def playable(board: BoardState, p: Coordinate) -> bool:
    # The physical function panel is never a game destination or area centre.
    return board.in_bounds(p) and p.col != 19


def free(board: BoardState, actors: Sequence[Actor], p: Coordinate, actor_id: str = "") -> bool:
    return playable(board, p) and not board.terrain_at(p).blocks_movement and not any(
        str(a.id) != actor_id and a.hp > 0 and a.position == p for a in actors)


def charge_paths(board: BoardState, actor: Actor, actors: Sequence[Actor], budget: int, *, parkour: bool = False) -> dict[Coordinate, ChargePath]:
    """Deterministic shortest paths, honoring terrain/edges except during Parkour.

    Parkour may cross enemies and obstacles, but not an occupied/blocked end.
    Ordinary movement reuses the world's corner/door and occupant legality.
    """
    if not playable(board, actor.position):
        return {}
    costs = {actor.position: 0}
    paths = {actor.position: ChargePath((), ())}
    queue = [(0, actor.position)]
    while queue:
        cost, p = heapq.heappop(queue)
        if cost != costs[p]:
            continue
        for q in neighbors(board, p):
            if not playable(board, q):
                continue
            occupant = next((a for a in actors if a.id != actor.id and a.hp > 0 and a.position == q), None)
            if parkour:
                if occupant and occupant.faction == actor.faction:
                    continue
                step = 1
            else:
                if not can_traverse(board, actor, actors, p, q):
                    continue
                step = 2 if board.terrain_at(q).is_difficult or occupant else 1
            total = cost + step
            if total > budget or total >= costs.get(q, budget+1):
                continue
            costs[q] = total
            paths[q] = ChargePath((*paths[p].cells, q), (*paths[p].costs, step))
            heapq.heappush(queue, (total, q))
    return {p: path for p, path in paths.items() if free(board, actors, p, str(actor.id))}
