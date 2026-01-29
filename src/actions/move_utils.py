"""Wspólne narzędzia do obsługi pętli ruchu bohatera."""

from __future__ import annotations

import logging
import heapq
from time import sleep
from typing import Callable, Iterable, Tuple

from board import consts

logger = logging.getLogger(__name__)

# Koszt ruchu w stopach: kardynał 5, diagonalnie naprzemiennie 5/10.
CARDINAL_COST_FEET = 5
DIAGONAL_COSTS_FEET = (5, 10)


def _is_diagonal(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] != b[0] and a[1] != b[1]


def step_cost_feet(
    current: tuple[int, int], neighbor: tuple[int, int], diagonal_parity: int
) -> tuple[int, int]:
    """Zwraca (koszt_w_stopach, nowy_parytet_diagonali)."""
    if _is_diagonal(current, neighbor):
        cost = DIAGONAL_COSTS_FEET[diagonal_parity % 2]
        return cost, 1 - diagonal_parity
    return CARDINAL_COST_FEET, diagonal_parity


def path_cost_feet(path: list[tuple[int, int]]) -> int:
    """Policz łączny dystans ścieżki w stopach zgodnie z zasadą 5/10 diagonalu."""
    if len(path) < 2:
        return 0
    total = 0
    parity = 0
    for idx in range(1, len(path)):
        step_cost, parity = step_cost_feet(path[idx - 1], path[idx], parity)
        total += step_cost
    return total


def trim_path_to_feet(path: list[tuple[int, int]], budget_feet: int) -> tuple[list[tuple[int, int]], int]:
    """Przytnij ścieżkę tak, by nie przekroczyć budżetu w stopach. Zwraca (przycięta_ścieżka, wykorzystane_stopy)."""
    if not path:
        return [], 0
    trimmed = [path[0]]
    used = 0
    parity = 0
    for idx in range(1, len(path)):
        step_cost, next_parity = step_cost_feet(path[idx - 1], path[idx], parity)
        if used + step_cost > budget_feet:
            break
        used += step_cost
        parity = next_parity
        trimmed.append(path[idx])
    return trimmed, used


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


def _feet_heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Zachowawcza heurystyka (5 stóp na każdy krok w osi lub przekątnej)."""
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return float(CARDINAL_COST_FEET) * max(dx, dy)


def find_path(
    board,
    start: tuple[int, int],
    goal: tuple[int, int],
    *,
    allow_diagonal: bool = True,
    allow_occupied: bool = True,
) -> list[tuple[int, int]] | None:
    """Znajdź najkrótszą ścieżkę (5 stóp kardynał, diagonal 5/10 naprzemiennie)."""
    if start == goal:
        return [start]
    if not (board.in_bounds(start) and board.in_bounds(goal)):
        return None

    open_set: list[tuple[float, tuple[int, int], int]] = []
    start_state = (start, 0)
    heapq.heappush(open_set, (0.0, start, 0))
    came_from: dict[tuple[tuple[int, int], int], tuple[tuple[int, int], int]] = {}
    g_score: dict[tuple[tuple[int, int], int], float] = {start_state: 0.0}
    best_goal_state: tuple[tuple[int, int], int] | None = None
    best_goal_cost = float("inf")

    while open_set:
        _f, current_pos, parity = heapq.heappop(open_set)
        current_state = (current_pos, parity)
        current_g = g_score.get(current_state)
        if current_g is None:
            continue

        if current_pos == goal:
            if current_g < best_goal_cost:
                best_goal_cost = current_g
                best_goal_state = current_state
            # heurystyka nie jest spójna między parytetami; kontynuujemy, ale możemy zakończyć
            if _f >= best_goal_cost:
                break
            continue

        for neighbor in board.get_neighbors(current_pos, include_position=False, diagonal=allow_diagonal):
            if not board.can_traverse(current_pos, neighbor, allow_occupied=allow_occupied):
                continue
            step_cost, next_parity = step_cost_feet(current_pos, neighbor, parity)
            neighbor_state = (neighbor, next_parity)
            tentative = g_score[current_state] + step_cost
            if tentative >= g_score.get(neighbor_state, float("inf")):
                continue
            came_from[neighbor_state] = current_state
            g_score[neighbor_state] = tentative
            f_score = tentative + _feet_heuristic(neighbor, goal)
            heapq.heappush(open_set, (f_score, neighbor, next_parity))
    if best_goal_state is None:
        return None
    path = [best_goal_state[0]]
    cursor = best_goal_state
    while cursor in came_from:
        cursor = came_from[cursor]
        path.append(cursor[0])
    path.reverse()
    return path


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
