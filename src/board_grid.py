from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import List, Optional, Protocol, Tuple
from interactable import Interactable

from obstacle import Obstacle
from wall import Wall


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
    interactables: list[Interactable] = dataclass_field(default_factory=list)


class BoardGrid:
    """Dwuwymiarowa siatka pól gry (pozycje przekazujemy jako krotki (col, row))."""

    def __init__(self, rows: int, cols: int):
        if rows <= 0 or cols <= 0:
            raise ValueError("Wymiary planszy muszą być dodatnie.")
        self.rows = rows  # liczba rzędów (drugi element w krotce pozycji)
        self.cols = cols  # liczba kolumn (pierwszy element w krotce pozycji)
        self._grid: List[List[GridCell]] = [
            [GridCell() for _ in range(cols)] for _ in range(rows)
        ]
        self.walls: dict[frozenset[Tuple[int, int]], Wall] = {}

    def in_bounds(self, position: Tuple[int, int]) -> bool:
        col, row = position
        return 0 <= row < self.rows and 0 <= col < self.cols

    def cell_at(self, position: Tuple[int, int]) -> GridCell:
        if not self.in_bounds(position):
            raise ValueError(f"Pozycja {position} znajduje się poza planszą.")
        col, row = position
        return self._grid[row][col]

    def set_field(self, position: Tuple[int, int], terrain: BasicTerrain) -> None:
        """Ustaw typ pola (np. teren nieprzechodni)."""
        cell = self.cell_at(position)
        cell.field = terrain

    def occupant_at(self, position: Tuple[int, int]) -> Optional[Occupant]:
        return self.cell_at(position).occupant

    def interactables_at(self, position: Tuple[int, int]) -> list[Interactable]:
        return list(self.cell_at(position).interactables)

    def get_neighbors(self, position: Tuple[int, int], include_position: bool = True, diagonal: bool = True) -> list[Tuple[int, int]]:
        """Zwróć pola sąsiadujące w obrębie planszy.

        diagonal=False – tylko ortogonalne (góra/dół/lewo/prawo).
        """
        if not self.in_bounds(position):
            raise ValueError(f"Pozycja {position} znajduje się poza planszą.")
        col, row = position
        offsets = (-1, 0, 1)
        result: list[Tuple[int, int]] = []
        if diagonal:
            for dr in offsets:
                for dc in offsets:
                    if dr == 0 and dc == 0:
                        continue
                    neighbor = (col + dc, row + dr)
                    if self.in_bounds(neighbor):
                        result.append(neighbor)
        else:
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                neighbor = (col + dc, row + dr)
                if self.in_bounds(neighbor):
                    result.append(neighbor)
        if include_position:
            result.append(position)
        return result

    def add_wall(
        self,
        a: Tuple[int, int],
        b: Tuple[int, int],
        *,
        hardness: int | None = None,
        features: Optional[dict[str, object]] = None,
        wall_cls: type[Wall] = Wall,
    ) -> Wall:
        """Dodaj ścianę blokującą przejście między polami."""
        if a == b:
            raise ValueError("Ściana musi łączyć dwa różne pola.")
        if not (self.in_bounds(a) and self.in_bounds(b)):
            raise ValueError("Ściana poza planszą.")
        wall = wall_cls(a=a, b=b, hardness=hardness, features=features or {})
        self.walls[wall.key] = wall
        return wall

    def get_wall(self, a: Tuple[int, int], b: Tuple[int, int]) -> Optional[Wall]:
        return self.walls.get(frozenset((a, b)))

    def is_blocked(self, a: Tuple[int, int], b: Tuple[int, int]) -> bool:
        return frozenset((a, b)) in self.walls

    def _is_obstacle(self, occupant: Optional[Occupant]) -> bool:
        return isinstance(occupant, Obstacle)

    def can_enter(self, position: Tuple[int, int], allow_occupied: bool = False) -> bool:
        """Sprawdź czy pole można zająć/przejść (teren przechodni, brak ściany i brak przeszkody)."""
        cell = self.cell_at(position)
        if not cell.field.walkable:
            return False
        if cell.occupant is None:
            return True
        if self._is_obstacle(cell.occupant):
            return False
        return allow_occupied

    def can_traverse(self, a: Tuple[int, int], b: Tuple[int, int], allow_occupied: bool = False) -> bool:
        """Czy z pola a można przejść na b (brak ściany, teren przechodni, brak przeszkody)."""
        if not (self.in_bounds(a) and self.in_bounds(b)):
            return False
        if self.is_blocked(a, b):
            return False
        return self.can_enter(b, allow_occupied=allow_occupied)

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

    def add_interactable(self, interactable: Interactable, position: Tuple[int, int]) -> None:
        cell = self.cell_at(position)
        cell.interactables.append(interactable)
        interactable.set_position(position)

    def remove_interactable(self, interactable: Interactable, position: Tuple[int, int]) -> None:
        cell = self.cell_at(position)
        if interactable in cell.interactables:
            cell.interactables.remove(interactable)
            interactable.set_position(None)

    def get_interactables_in_range(
        self, position: Tuple[int, int], *, include_position: bool = True, diagonal: bool = True
    ) -> list[Tuple[int, int]]:
        """Zwróć pozycje z obiektami interaktywnymi w zasięgu sąsiadów."""
        result: list[Tuple[int, int]] = []
        for candidate in self.get_neighbors(position, include_position=include_position, diagonal=diagonal):
            if self.interactables_at(candidate):
                result.append(candidate)
        return result
    
    def move(self, source: Tuple[int, int], target: Tuple[int, int]) -> None:
        occupant = self.occupant_at(source)
        if occupant is None:
            raise ValueError(f"Brak obiektu do przeniesienia z pola {source}.")
        self.remove(source)
        self.place(occupant, target)
