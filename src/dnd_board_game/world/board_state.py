from __future__ import annotations

from dataclasses import dataclass, field

from .coordinates import BoardDimensions, Coordinate
from .terrain import NORMAL_TERRAIN, Terrain


Edge = frozenset[Coordinate]


def edge_between(a: Coordinate, b: Coordinate) -> Edge:
    if a == b:
        raise ValueError("An edge must connect two different coordinates.")
    return frozenset((a, b))


@dataclass(frozen=True, slots=True)
class Door:
    is_open: bool = False


@dataclass(slots=True)
class BoardState:
    dimensions: BoardDimensions = field(default_factory=BoardDimensions)
    terrain_by_tile: dict[Coordinate, Terrain] = field(default_factory=dict)
    walls: set[Edge] = field(default_factory=set)
    doors: dict[Edge, Door] = field(default_factory=dict)

    def in_bounds(self, coordinate: Coordinate) -> bool:
        return self.dimensions.in_bounds(coordinate)

    def terrain_at(self, coordinate: Coordinate) -> Terrain:
        if not self.in_bounds(coordinate):
            raise ValueError(f"Coordinate out of bounds: {coordinate}.")
        return self.terrain_by_tile.get(coordinate, NORMAL_TERRAIN)

    def set_terrain(self, coordinate: Coordinate, terrain: Terrain) -> None:
        if not self.in_bounds(coordinate):
            raise ValueError(f"Coordinate out of bounds: {coordinate}.")
        self.terrain_by_tile[coordinate] = terrain

    def add_wall(self, a: Coordinate, b: Coordinate) -> None:
        self._validate_adjacent(a, b)
        self.walls.add(edge_between(a, b))

    def set_door(self, a: Coordinate, b: Coordinate, *, is_open: bool) -> None:
        self._validate_adjacent(a, b)
        key = edge_between(a, b)
        self.walls.discard(key)
        self.doors[key] = Door(is_open=is_open)

    def blocks_edge(self, a: Coordinate, b: Coordinate) -> bool:
        key = edge_between(a, b)
        if key in self.walls:
            return True
        door = self.doors.get(key)
        return bool(door is not None and not door.is_open)

    def _validate_adjacent(self, a: Coordinate, b: Coordinate) -> None:
        if not (self.in_bounds(a) and self.in_bounds(b)):
            raise ValueError("Edge coordinates must be in bounds.")
        dc = abs(a.col - b.col)
        dr = abs(a.row - b.row)
        if dc + dr != 1:
            raise ValueError("Edges can only connect orthogonally adjacent coordinates.")
