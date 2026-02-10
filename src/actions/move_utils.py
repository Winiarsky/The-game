from __future__ import annotations

import logging
import time
from collections import deque

logger = logging.getLogger(__name__)


def find_path(board, start, goal, *, allow_diagonal: bool = True, allow_occupied: bool = True):
    """Znajdź najkrótszą ścieżkę BFS-em, respektując blokady planszy."""
    if start == goal:
        return [start]
    if not (board.in_bounds(start) and board.in_bounds(goal)):
        return []

    def _neighbors(pos):
        x, y = pos
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if allow_diagonal:
            deltas += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dx, dy in deltas:
            yield x + dx, y + dy

    visited = {start: None}
    q = deque([start])

    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for nxt in _neighbors(cur):
            if not board.in_bounds(nxt):
                continue
            try:
                if board.is_blocked(cur, nxt):
                    continue
            except Exception:
                pass
            try:
                if not allow_occupied and not board.can_enter(nxt, allow_occupied=False):
                    continue
            except Exception:
                pass
            if nxt in visited:
                continue
            visited[nxt] = cur
            q.append(nxt)

    if goal not in visited:
        return []

    # reconstruct
    rev = []
    cur = goal
    while cur is not None:
        rev.append(cur)
        cur = visited[cur]
    return list(reversed(rev))


def path_cost_feet(path):
    """Koszt w stopach (5 ft per krawędź)."""
    return max(0, (len(path) - 1) * 5)


def trim_path_to_feet(path, max_feet):
    """Przytnij ścieżkę do dostępnej liczby stóp."""
    if max_feet <= 0 or len(path) < 2:
        return [path[0]] if path else []
    max_edges = max_feet // 5
    return path[: max_edges + 1]


def follow_path(ctx_or_board, mover, path, *, led_color=None, on_enter=None, allow_occupied=True, step_delay: float = 0.0):
    """Wykonaj ruch po ścieżce krok po kroku.

    Zwraca (completed: bool, stop_pos, reason:str|None) zgodnie z oczekiwaniami eventów.
    Obsługuje blokady planszy, kolizje oraz hook on_enter (np. wejście do pokoju -> walka).
    """
    if not path or len(path) < 2:
        return False, path[0] if path else None, "move_error"

    board = getattr(getattr(ctx_or_board, "game", None), "board", None) or ctx_or_board
    current = path[0]

    for step in path[1:]:
        try:
            if board is not None and hasattr(board, "is_blocked") and board.is_blocked(current, step):
                return False, current, "blocked"
        except Exception:
            pass
        try:
            if board is not None and hasattr(board, "can_enter") and not board.can_enter(step, allow_occupied=allow_occupied):
                return False, current, "occupied"
        except Exception:
            pass

        prev = current
        try:
            mover.position = step  # type: ignore[attr-defined]
        except Exception:
            pass
        try:
            if board is not None and hasattr(board, "move"):
                board.move(prev, step)
        except Exception as exc:
            logger.debug("board.move failed: %s", exc)
            return False, prev, "move_error"

        if callable(on_enter):
            try:
                stop = on_enter(ctx_or_board, mover, step)
                if stop:
                    return False, step, "on_enter"
            except Exception as exc:
                logger.debug("on_enter hook failed: %s", exc)
                return False, step, "on_enter"

        if step_delay:
            time.sleep(step_delay)

        current = step

    return True, current, None


def perform_movement(ctx, hero, start_pos, neighbors_fn, *, led_color=None, end_message=None, allow_occupied=True, on_enter=None):
    """Stub ruchu: pozostawia bohatera na miejscu; zwraca start_pos."""
    return start_pos


def default_on_enter(*_args, **_kwargs):
    return None


def _maybe_dispatch_move_reactions(*_args, **_kwargs):
    """Brak reakcji w stubie."""
    return None
