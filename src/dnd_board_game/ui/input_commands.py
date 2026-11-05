"""Device-neutral, transient input state; no game rules or device access."""
from __future__ import annotations

from dataclasses import dataclass

from dnd_board_game.world import Coordinate


@dataclass(slots=True)
class CursorState:
    revision: int = 0
    context: str = ""
    position: Coordinate | None = None
    touched: bool = False


def cursor_step(origin: Coordinate, dx: int, dy: int, *, cols: int = 20,
                rows: int = 30) -> Coordinate:
    """A cursor crosses obstacles, stays within the map and skips the panel."""
    if type(dx) is not int or type(dy) is not int or abs(dx) > 1 or abs(dy) > 1:
        raise ValueError("Kierunek kursora musi wskazywać sąsiednie pole.")
    col = max(0, min(cols - 1, origin.col + dx))
    if col == 19:
        col = origin.col
    return Coordinate(col, max(0, min(rows - 1, origin.row + dy)))


def cursor_position(value: object, *, cols: int = 20, rows: int = 30) -> Coordinate:
    if (not isinstance(value, (list, tuple)) or len(value) != 2
            or any(type(n) is not int for n in value)):
        raise ValueError("Nieprawidłowe współrzędne kursora.")
    col, row = value
    if not (0 <= col < cols and 0 <= row < rows) or col == 19:
        raise ValueError("Kursor musi pozostać na mapie, poza panelem run.")
    return Coordinate(col, row)
