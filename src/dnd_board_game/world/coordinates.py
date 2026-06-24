from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True, slots=True)
class Coordinate:
    col: int
    row: int

    def __iter__(self):
        yield self.col
        yield self.row

    def as_tuple(self) -> tuple[int, int]:
        return (self.col, self.row)


@dataclass(frozen=True, slots=True)
class BoardDimensions:
    cols: int = 20
    rows: int = 30

    def __post_init__(self) -> None:
        if self.cols <= 0 or self.rows <= 0:
            raise ValueError("Board dimensions must be positive.")

    def in_bounds(self, coordinate: Coordinate) -> bool:
        return 0 <= coordinate.col < self.cols and 0 <= coordinate.row < self.rows
