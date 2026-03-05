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


def _safe_int(value, default=0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _status_first_int(mover, key: str):
    for data in _iter_status_data(mover):
        if key in data:
            try:
                return int(data.get(key))
            except Exception:
                continue
    return None


def _status_max_int(mover, key: str, default: int = 0) -> int:
    best = int(default)
    for data in _iter_status_data(mover):
        if key not in data:
            continue
        try:
            value = int(data.get(key) or 0)
        except Exception:
            value = 0
        if value > best:
            best = value
    return best


def _status_sum_int(mover, key: str, default: int = 0) -> int:
    total = int(default)
    for data in _iter_status_data(mover):
        if key not in data:
            continue
        try:
            value = int(data.get(key) or 0)
        except Exception:
            value = 0
        total += value
    return int(total)


def _status_any_true(mover, key: str) -> bool:
    for data in _iter_status_data(mover):
        if bool(data.get(key, False)):
            return True
    return False


def base_speed_feet(mover, default_feet: int = 25) -> int:
    """Bazowa prędkość aktora w stopach."""
    if mover is None:
        return max(0, _safe_int(default_feet, 25))

    base = None
    for attr in ("base_speed_feet", "land_speed_feet"):
        raw = getattr(mover, attr, None)
        if raw is not None:
            val = _safe_int(raw, 0)
            if val > 0:
                base = val
                break

    if base is None:
        status_speed = _status_first_int(mover, "base_speed_feet")
        if status_speed is not None and status_speed > 0:
            base = status_speed

    if base is None:
        # kompatybilność z istniejącymi enemy statami
        distance = getattr(mover, "distance", None)
        if distance is not None:
            val = _safe_int(distance, 0)
            if val > 0:
                base = val

    if base is None:
        move_points = getattr(mover, "move_points", None)
        if move_points is not None:
            val = _safe_int(move_points, 0) * 5
            if val > 0:
                base = val

    if base is None:
        base = max(0, _safe_int(default_feet, 25))
    base += max(0, _status_sum_int(mover, "base_speed_bonus_feet", default=0))
    return max(0, int(base))


def movement_budget_feet(mover, *, default_feet: int = 25) -> int:
    """Policz budżet ruchu: base speed + bonus - penalty."""
    base = base_speed_feet(mover, default_feet=default_feet)
    if mover is None:
        return max(0, base)

    try:
        from statuses import speed_bonus_value, speed_penalty_value
    except Exception:
        speed_bonus_value = lambda _actor: 0  # type: ignore[assignment]
        speed_penalty_value = lambda _actor: 0  # type: ignore[assignment]

    bonus = max(0, _safe_int(speed_bonus_value(mover), 0))
    penalty = max(0, _safe_int(speed_penalty_value(mover), 0))

    armor_penalty = 0
    for attr in ("armor_speed_penalty_feet", "speed_penalty_armor_feet"):
        raw = getattr(mover, attr, None)
        if raw is not None:
            armor_penalty = max(armor_penalty, max(0, _safe_int(raw, 0)))
    if _status_any_true(mover, "ignore_armor_move_penalty"):
        armor_penalty = 0

    # Unburdened Iron: redukcja jednej kary do speed o 5.
    slow_reduction = _status_max_int(mover, "magical_slow_reduction_feet", default=0)
    reduced_penalty = penalty
    if slow_reduction > 0 and reduced_penalty > 0:
        reduced_penalty = max(0, reduced_penalty - slow_reduction)

    total = base + bonus - reduced_penalty - armor_penalty
    return max(0, int(total))


def forced_movement_distance_feet(target, base_feet: int) -> int:
    """Skoryguj dystans forced movement na podstawie statusów celu."""
    base = max(0, _safe_int(base_feet, 0))
    if target is None or base <= 0:
        return base

    multiplier = 1.0
    for data in _iter_status_data(target):
        if "forced_movement_multiplier" not in data:
            continue
        try:
            mult = float(data.get("forced_movement_multiplier"))
        except Exception:
            continue
        if mult <= 0:
            continue
        threshold = _safe_int(data.get("forced_movement_threshold_feet"), 0)
        if threshold > 0 and base < threshold:
            continue
        multiplier = min(multiplier, mult)

    adjusted = int(base * multiplier)
    return max(0, adjusted)


def adjusted_forced_movement_squares(target, squares: int) -> int:
    """Przelicz forced movement w polach (1 pole = 5 ft)."""
    base = max(0, _safe_int(squares, 0))
    if base <= 0:
        return 0
    feet = forced_movement_distance_feet(target, base * 5)
    return max(0, feet // 5)


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

        try:
            from GameObjects.events.magic.runtime_effects import process_alarm_wards_for_move

            game = getattr(ctx_or_board, "game", None)
            process_alarm_wards_for_move(game, mover, step)
        except Exception:
            pass

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
    game = getattr(ctx_or_board, "game", None)
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
            result = on_enter(mover, game)
            try:
                if game is not None:
                    from GameObjects.events.magic.lighting_effects import apply_lighting_to_actor

                    apply_lighting_to_actor(game, mover)
            except Exception:
                pass
            return result
        except Exception as exc:
            logger.debug("terrain.on_enter failed: %s", exc)
    return None


def _maybe_dispatch_move_reactions(ctx, mover, src, dst, *, action_tags=None):
    """Obsłuż reakcje na zakończenie ruchu (np. Goblin Scuttle)."""
    game = getattr(ctx, "game", None) or getattr(ctx, "game", None)
    if game is None:
        return None
    state = getattr(game, "state", None)
    if getattr(getattr(state, "__class__", None), "__name__", "") != "Combat":
        return None
    if mover not in getattr(game, "heroes", []):
        return None
    if dst is None:
        return None

    def _has_status(actor, status_id: str) -> bool:
        has_status = getattr(actor, "has_status", None)
        if callable(has_status):
            try:
                return bool(has_status(status_id))
            except Exception:
                return False
        statuses = getattr(actor, "statuses", None)
        if isinstance(statuses, list):
            return any(getattr(s, "id", s) == status_id for s in statuses)
        return False

    def _adjacent(a, b) -> bool:
        if a is None or b is None:
            return False
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy) <= 1

    scuttlers = [
        hero
        for hero in getattr(game, "heroes", [])
        if hero is not mover and _has_status(hero, "goblin_scuttle")
    ]
    if not scuttlers:
        return None

    for scuttler in scuttlers:
        pos = getattr(scuttler, "position", None)
        if pos is None or not _adjacent(pos, dst):
            continue
        try:
            ui = getattr(game, "ui", None)
            if ui is not None and hasattr(ui, "prompt_info"):
                ui.prompt_info(
                    "Goblin Scuttle",
                    prompt_long=(
                        f"{getattr(scuttler, 'name', 'Bohater')} może wykonać Step "
                        f"po ruchu {getattr(mover, 'name', 'sojusznika')}."
                    ),
                    source="goblin_scuttle",
                )
            else:
                game.ui_log(
                    f"Goblin Scuttle: {getattr(scuttler, 'name', 'Bohater')} może wykonać Step."
                )
        except Exception:
            pass

        try:
            from GameObjects.events.step_event import StepEvent
            from GameObjects.events.base import EventContext

            StepEvent().execute(EventContext(game=game, actor=scuttler))
            game.ui_log(
                f"Goblin Scuttle: {getattr(scuttler, 'name', 'Bohater')} wykonuje Step."
            )
            game.ui_log(
                f"Powrót do ruchu {getattr(mover, 'name', 'sojusznika')}."
            )
        except Exception:
            pass
    return None
