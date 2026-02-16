from __future__ import annotations

import logging
import time
import heapq

logger = logging.getLogger(__name__)


def _is_diagonal(a, b) -> bool:
    return abs(a[0] - b[0]) == 1 and abs(a[1] - b[1]) == 1


def _iter_status_data(mover):
    statuses = getattr(mover, "statuses", None) or []
    for status in statuses:
        data = getattr(status, "data", None)
        if isinstance(data, dict):
            yield data


def _ignores_terrain_move_cost(mover, terrain) -> bool:
    if mover is None or terrain is None:
        return False
    terrain_name = getattr(terrain, "name", None)
    terrain_tags = set(getattr(terrain, "terrain_tags", ()) or ())
    for data in _iter_status_data(mover):
        names = data.get("ignore_move_cost_terrain_names") or []
        if terrain_name and terrain_name in names:
            return True
        tags = data.get("ignore_move_cost_terrain_tags") or []
        if tags and terrain_tags.intersection(tags):
            return True
    return False


def terrain_move_bonus_feet(board, pos, mover=None) -> int:
    try:
        terrain = board.cell_at(pos).field
    except Exception:
        return 0
    bonus = int(getattr(terrain, "move_cost_bonus_feet", 0) or 0)
    if bonus <= 0:
        return 0
    if mover is not None and _ignores_terrain_move_cost(mover, terrain):
        return 0
    return bonus


def find_path(board, start, goal, *, allow_diagonal: bool = True, allow_occupied: bool = True, mover=None):
    """Znajdź najtańszą ścieżkę (Dijkstra) z uwzględnieniem kosztu terenu i skosów 5/10."""
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

    def _step_cost(src, dst, diag_parity):
        is_diag = _is_diagonal(src, dst)
        cost = 10 if (is_diag and diag_parity == 1) else 5
        cost += terrain_move_bonus_feet(board, dst, mover)
        next_parity = diag_parity ^ 1 if is_diag else diag_parity
        return cost, next_parity

    prev: dict[tuple[tuple[int, int], int], tuple[tuple[int, int], int] | None] = {(start, 0): None}
    cost_so_far: dict[tuple[tuple[int, int], int], int] = {(start, 0): 0}
    heap = [(0, start, 0)]

    while heap:
        cur_cost, cur, parity = heapq.heappop(heap)
        if cur == goal:
            break
        if cur_cost != cost_so_far.get((cur, parity)):
            continue
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
            step_cost, next_parity = _step_cost(cur, nxt, parity)
            new_cost = cur_cost + step_cost
            state = (nxt, next_parity)
            if new_cost < cost_so_far.get(state, float("inf")):
                cost_so_far[state] = new_cost
                prev[state] = (cur, parity)
                heapq.heappush(heap, (new_cost, nxt, next_parity))

    goal_states = [state for state in cost_so_far.keys() if state[0] == goal]
    if not goal_states:
        return []
    best_state = min(goal_states, key=lambda st: cost_so_far.get(st, float("inf")))

    # reconstruct
    rev = []
    cur = best_state
    while cur is not None:
        rev.append(cur[0])
        cur = prev[cur]
    return list(reversed(rev))


def path_cost_feet(path, board=None, mover=None):
    """Koszt w stopach (skosy 5/10 + koszt terenu)."""
    if not path or len(path) < 2:
        return 0
    diag_parity = 0
    bonus = 0
    total = 0
    for prev, step in zip(path, path[1:]):
        is_diag = _is_diagonal(prev, step)
        step_cost = 10 if (is_diag and diag_parity == 1) else 5
        if is_diag:
            diag_parity ^= 1
        if board is not None and hasattr(board, "cell_at"):
            bonus = terrain_move_bonus_feet(board, step, mover)
        else:
            bonus = 0
        total += step_cost + bonus
    return max(0, total)


def trim_path_to_feet(path, max_feet, board=None, mover=None):
    """Przytnij ścieżkę do dostępnej liczby stóp."""
    if max_feet <= 0 or len(path) < 2:
        return [path[0]] if path else []
    total = 0
    trimmed = [path[0]]
    diag_parity = 0
    for prev, step in zip(path, path[1:]):
        is_diag = _is_diagonal(prev, step)
        step_cost = 10 if (is_diag and diag_parity == 1) else 5
        if is_diag:
            diag_parity ^= 1
        if board is not None and hasattr(board, "cell_at"):
            step_cost += terrain_move_bonus_feet(board, step, mover)
        if total + step_cost > max_feet:
            break
        total += step_cost
        trimmed.append(step)
    return trimmed


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


def default_on_enter(ctx_or_board, mover, position):
    board = getattr(getattr(ctx_or_board, "game", None), "board", None)
    if board is None and hasattr(ctx_or_board, "cell_at"):
        board = ctx_or_board
    if board is None or mover is None:
        return None
    try:
        terrain = board.cell_at(position).field
    except Exception:
        return None
    on_enter = getattr(terrain, "on_enter", None)
    if callable(on_enter):
        try:
            return on_enter(mover, getattr(ctx_or_board, "game", None))
        except Exception as exc:
            logger.debug("terrain.on_enter failed: %s", exc)
    return None


def _maybe_dispatch_move_reactions(*_args, **_kwargs):
    """Brak reakcji w stubie."""
    return None
