"""Wspólne narzędzia do obsługi pętli ruchu bohatera."""

from __future__ import annotations

import logging
import heapq
from time import sleep
from typing import Callable, Iterable, Tuple

from board import consts

logger = logging.getLogger(__name__)

# Przybliżony koszt przekątnej (sqrt(2)), wystarczający do wyznaczania ścieżki.
DIAGONAL_COST = 1.4


def default_on_enter(ctx, hero, current_pos: Tuple[int, int]) -> bool:
    """Wyzwala on_enter obiektów na polu; zwraca True, gdy coś przerwało ruch."""
    triggered = False
    board = ctx.game.board
    cell = board.cell_at(current_pos)
    field_handler = getattr(cell.field, "on_enter", None)
    if callable(field_handler):
        msg = field_handler(hero, ctx.game)
        if msg:
            logger.info(msg)
            triggered = True
    for obj in board.interactables_at(current_pos):
        was_hidden = getattr(obj, "hidden", False) and not getattr(obj, "revealed", False)
        on_enter = getattr(obj, "on_enter", None)
        if callable(on_enter):
            result = on_enter(hero, ctx.game)
            if result:
                logger.info(result)
                triggered = True
            if was_hidden and getattr(obj, "revealed", False):
                ctx.game.conn.set_leds([current_pos], consts.HIDDEN_REVEAL_RGB)
                sleep(consts.RESPONSE_DELAY)
                ctx.game.conn.leds_off()
    return triggered


def perform_movement(
    ctx,
    hero,
    start_pos: Tuple[int, int],
    get_neighbors: Callable[[Tuple[int, int]], Iterable[Tuple[int, int]]],
    *,
    led_color: list[int],
    end_message: str,
    allow_occupied: bool = True,
    on_enter: Callable[[object, object, Tuple[int, int]], bool] = default_on_enter,
) -> None:
    """Pętla ruchu współdzielona między akcjami (Move/Stealth).

    get_neighbors – funkcja zwracająca listę dozwolonych sąsiadów (łącznie z bieżącym polem jako opcją zakończenia).
    on_enter – hook po wejściu na pole; jeśli zwróci True, ruch się kończy.
    """
    board = ctx.game.board
    current_pos = start_pos
    source_pos = start_pos

    while True:
        valid_neighbors = list(get_neighbors(current_pos))
        ctx.game.conn.set_leds(valid_neighbors, led_color)
        target = ctx.game.conn.scan_board(valid_neighbors)
        ctx.game.conn.leds_off()
        if target == current_pos:
            logger.info(end_message)
            return

        if not board.can_traverse(current_pos, target, allow_occupied=allow_occupied):
            logger.info("Nie można wejść na to pole.")
            continue

        occupant = board.occupant_at(target)
        if occupant is not None and occupant is not hero:
            # Przechodzimy przez pole zajęte, ale nie kończymy na nim.
            current_pos = target
            continue

        try:
            board.move(source_pos, target)
        except ValueError as exc:
            logger.error("Nie można wykonać ruchu: %s", exc)
            continue

        source_pos = target
        current_pos = target
        if on_enter(ctx, hero, current_pos):
            logger.info("Ruch zakończony na %s przez zdarzenie na polu.", current_pos)
            return


def _octile_heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Heurystyka dla siatki z przekątnymi."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return max(dx, dy) + (DIAGONAL_COST - 1.0) * min(dx, dy)


def find_path(
    board,
    start: tuple[int, int],
    goal: tuple[int, int],
    *,
    allow_diagonal: bool = True,
    allow_occupied: bool = True,
) -> list[tuple[int, int]] | None:
    """Znajdź najkrótszą ścieżkę A* między polami (łącznie ze startem i celem)."""
    if start == goal:
        return [start]
    if not (board.in_bounds(start) and board.in_bounds(goal)):
        return None

    open_set: list[tuple[float, tuple[int, int]]] = []
    heapq.heappush(open_set, (0.0, start))
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], float] = {start: 0.0}

    while open_set:
        _f, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        for neighbor in board.get_neighbors(current, include_position=False, diagonal=allow_diagonal):
            if not board.can_traverse(current, neighbor, allow_occupied=allow_occupied):
                continue
            step_cost = 1.0 if (neighbor[0] == current[0] or neighbor[1] == current[1]) else DIAGONAL_COST
            tentative = g_score[current] + step_cost
            if tentative >= g_score.get(neighbor, float("inf")):
                continue
            came_from[neighbor] = current
            g_score[neighbor] = tentative
            f_score = tentative + _octile_heuristic(neighbor, goal)
            heapq.heappush(open_set, (f_score, neighbor))
    return None


def follow_path(
    ctx,
    hero,
    path: list[tuple[int, int]],
    *,
    led_color: list[int],
    on_enter: Callable[[object, object, Tuple[int, int]], bool] = default_on_enter,
    allow_occupied: bool = True,
    step_delay: float = 0.0,
) -> tuple[bool, tuple[int, int] | None, str | None]:
    """Wykonaj ruch wzdłuż wyznaczonej ścieżki.

    Zwraca (ukończono_całość, ostatnia_pozycja, powód_przerwania).
    Powody: blocked (ściana/teren), occupied, move_error, on_enter.
    """
    if not path:
        return False, None, "blocked"
    if len(path) == 1:
        return True, path[0], None

    board = ctx.game.board
    current = path[0]
    remaining = list(path[1:])
    ctx.game.conn.set_leds(remaining, led_color)
    try:
        for idx, step in enumerate(remaining):
            if not board.can_traverse(current, step, allow_occupied=allow_occupied):
                return False, current, "blocked"

            try:
                board.move(current, step)
            except ValueError as exc:
                logger.error("Nie można wykonać ruchu na %s: %s", step, exc)
                return False, current, "move_error"

            previous = current
            current = step
            if on_enter(ctx, hero, current):
                return False, current, "on_enter"

            tail = remaining[idx + 1 :]
            ctx.game.conn.set_leds([previous], [0, 0, 0])
            if step_delay > 0:
                sleep(step_delay)
            if tail:
                ctx.game.conn.set_leds(tail, led_color)
        return True, current, None
    finally:
        try:
            ctx.game.conn.set_leds(path, [0, 0, 0])
        except Exception:
            pass
