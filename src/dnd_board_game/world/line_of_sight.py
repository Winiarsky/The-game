from __future__ import annotations

from .board_state import BoardState
from .coordinates import Coordinate


def bresenham_line(start: Coordinate, end: Coordinate) -> tuple[Coordinate, ...]:
    x0, y0 = start.col, start.row
    x1, y1 = end.col, end.row
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    cells: list[Coordinate] = [Coordinate(x0, y0)]
    while (x0, y0) != (x1, y1):
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
        cells.append(Coordinate(x0, y0))
    return tuple(cells)


def line_of_sight_clear(board: BoardState, start: Coordinate, end: Coordinate) -> bool:
    if not board.in_bounds(start) or not board.in_bounds(end):
        return False
    if start == end:
        return True
    line = bresenham_line(start, end)
    for index, cell in enumerate(line[1:], start=1):
        previous = line[index - 1]
        if not _can_project_between(board, previous, cell):
            return False
        if cell != end and board.terrain_at(cell).blocks_movement:
            return False
    return True


def _can_project_between(board: BoardState, start: Coordinate, end: Coordinate) -> bool:
    dc = abs(start.col - end.col)
    dr = abs(start.row - end.row)
    if max(dc, dr) != 1:
        return False
    if dc + dr == 1:
        return not board.blocks_edge(start, end)
    side_a = Coordinate(end.col, start.row)
    side_b = Coordinate(start.col, end.row)
    return not (board.blocks_edge(start, side_a) and board.blocks_edge(start, side_b))
