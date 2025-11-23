from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import List, Optional, Protocol, Tuple


class Occupant(Protocol):
    position: Optional[Tuple[int, int]]

    def set_position(self, position: Optional[Tuple[int, int]]) -> None: ...


@dataclass(slots=True) # do przeneisienia do innego folderu
class BasicTerrain:
    name: str = "basic"
    walkable: bool = True


@dataclass(slots=True)
class GridCell:
    field: BasicTerrain = dataclass_field(default_factory=BasicTerrain)
    occupant: Optional[Occupant] = None 
    # trzeba bedze dodać inne rzeczy jak przeszkody, skarby itp.


class BoardGrid:
    """Dwuwymiarowa siatka pól gry."""

    def __init__(self, rows: int, cols: int):
        if rows <= 0 or cols <= 0:
            raise ValueError("Wymiary planszy muszą być dodatnie.")
        self.rows = rows
        self.cols = cols
        self._grid: List[List[GridCell]] = [
            [GridCell() for _ in range(cols)] for _ in range(rows)
        ]

    def in_bounds(self, position: Tuple[int, int]) -> bool:
        row, col = position
        return 0 <= row < self.rows and 0 <= col < self.cols

    def cell_at(self, position: Tuple[int, int]) -> GridCell:
        if not self.in_bounds(position):
            raise ValueError(f"Pozycja {position} znajduje się poza planszą.")
        row, col = position
        return self._grid[row][col]

    def occupant_at(self, position: Tuple[int, int]) -> Optional[Occupant]:
        return self.cell_at(position).occupant

    def get_neighbors(self, position: Tuple[int, int], include_position: bool = True) -> list[Tuple[int, int]]:
        """Zwróć wszystkie pola sąsiadujące (również po skosie) w obrębie planszy."""
        if not self.in_bounds(position):
            raise ValueError(f"Pozycja {position} znajduje się poza planszą.")
        row, col = position
        offsets = (-1, 0, 1)
        result: list[Tuple[int, int]] = []
        for dr in offsets:
            for dc in offsets:
                if dr == 0 and dc == 0:
                    continue
                neighbor = (row + dr, col + dc)
                if self.in_bounds(neighbor):
                    result.append(neighbor)
        if include_position:
            result.append(position)
        return result

    def place(self, occupant: Occupant, position: Tuple[int, int]) -> None:
        cell = self.cell_at(position)
        if cell.occupant is not None:
            raise ValueError(f"Pole {position} jest już zajęte.")
        cell.occupant = occupant
        occupant.set_position(position)

    def remove(self, position: Tuple[int, int]) -> Optional[Occupant]:
        cell = self.cell_at(position)
        occupant = cell.occupant
        if occupant is not None:
            cell.occupant = None
            occupant.set_position(None)
        return occupant
    
    def move(self, source: Tuple[int, int], target: Tuple[int, int]) -> None:
        occupant = self.occupant_at(source)
        if occupant is None:
            raise ValueError(f"Brak obiektu do przeniesienia z pola {source}.")
        self.remove(source)
        self.place(occupant, target)