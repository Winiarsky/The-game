import logging
from time import sleep
from typing import Iterable, Tuple

from actions.attack import _choose_enemy
from board import consts
from GameObjects.interactions_mixin import prompt_for_roll
from .registry import register_special

logger = logging.getLogger(__name__)

MISSILE_RGB = [180, 0, 180]
MISSILE_STEP_DELAY = 0.15


def _can_traverse(board, a: tuple[int, int], b: tuple[int, int], goal: tuple[int, int]) -> bool:
    """Wariant can_traverse pozwalający wejść na cel nawet jeśli blokuje ruch."""
    if not (board.in_bounds(a) and board.in_bounds(b)):
        return False
    if board.is_blocked(a, b):
        return False
    for edge_obj in board.edge_interactables_between(a, b):
        blocks_passage = getattr(edge_obj, "blocks_passage", None)
        if callable(blocks_passage) and blocks_passage(a, b):
            return False
    cell = board.cell_at(b)
    if not cell.field.walkable:
        return False
    if any(getattr(obj, "blocks_movement", False) or not getattr(obj, "allow_same_cell_interact", True) for obj in cell.interactables):
        return False
    if cell.occupant is None:
        return True
    # pozwól wejść na cel niezależnie od blokady ruchu
    if b == goal:
        return True
    occupant = cell.occupant
    from GameObjects.Obstacles.basic_obstacle import Obstacle  # lokalny import żeby uniknąć cykli

    if isinstance(occupant, Obstacle):
        return False
    if getattr(occupant, "blocks_movement", False):
        return False
    return False  # nie przechodzimy przez inne zajęte pola


def _find_path(board, start: tuple[int, int], goal: tuple[int, int], *, allow_diagonal: bool = True) -> list[tuple[int, int]] | None:
    """A* z respektowaniem ścian/terenów i blokad, ale pozwalający skończyć na zajętym polu celu."""
    if start == goal:
        return [start]
    if not (board.in_bounds(start) and board.in_bounds(goal)):
        return None

    import heapq

    def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy) + (1.4 - 1.0) * min(dx, dy)

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

        neighbors: Iterable[Tuple[int, int]] = board.get_neighbors(current, include_position=False, diagonal=allow_diagonal)
        for neighbor in neighbors:
            if not _can_traverse(board, current, neighbor, goal):
                continue
            step_cost = 1.0 if (neighbor[0] == current[0] or neighbor[1] == current[1]) else 1.4
            tentative = g_score[current] + step_cost
            if tentative >= g_score.get(neighbor, float("inf")):
                continue
            came_from[neighbor] = current
            g_score[neighbor] = tentative
            f_score = tentative + heuristic(neighbor, goal)
            heapq.heappush(open_set, (f_score, neighbor))
    return None


def _animate_path(conn, path: list[tuple[int, int]]) -> None:
    """Prosta animacja pocisku po ścieżce, bez globalnego leds_off dla płynności."""
    if not path or len(path) < 2:
        return
    previous = path[0]
    # zapal start
    conn.set_leds([previous], MISSILE_RGB)
    try:
        for step in path[1:]:
            positions = [step]
            colors = [MISSILE_RGB]
            if previous is not None:
                positions.insert(0, previous)
                colors.insert(0, [0, 0, 0])  # gaś poprzedni w tym samym wywołaniu
            conn.set_leds(positions, colors)
            previous = step
            sleep(MISSILE_STEP_DELAY)
    finally:
        try:
            conn.set_leds(path, [0, 0, 0])
        except Exception:
            pass


@register_special(
    "magic_missile",
    name="Magic Missle",
    aliases=["magic missle", "magic_missle", "magic missile"],
    description="Wybierz cel, wyznacz ścieżkę i zadaj obrażenia magiczne.",
)
def magic_missile_ability(hero, ctx) -> bool:
    """Pocisk magiczny szukający ścieżki do wroga i zadający obrażenia."""
    game = ctx.game
    conn = game.conn
    board = game.board
    start_pos = getattr(hero, "position", None)
    if start_pos is None:
        logger.info("Bohater nie ma pozycji – nie można użyć Magic Missle.")
        game.ui_log("Nie możesz użyć Magic Missle bez pozycji bohatera.")
        return False

    enemy, enemy_pos = _choose_enemy(ctx)
    if enemy is None or enemy_pos is None:
        logger.info("Nie wybrano celu dla Magic Missle.")
        return False

    path = _find_path(board, start_pos, enemy_pos, allow_diagonal=True)
    if not path or len(path) < 2:
        logger.info("Brak możliwej ścieżki dla Magic Missle.")
        game.ui_log("Brak możliwej ścieżki – pocisk nie może dotrzeć do celu.")
        return False

    # Rzut na obrażenia – gracz podaje wynik k4 (lub inny, wg mocy czaru).
    dmg = prompt_for_roll("Magic Missle: podaj wynik k4 (lub modyfikowany) obrażeń: ")
    logger.info("Magic Missle zadaje %s obrażeń magicznych wzdłuż ścieżki %s.", dmg, path)
    game.ui_log(f"Magic Missle leci do {getattr(enemy, 'name', 'wroga')} (obrażenia: {dmg}).")

    _animate_path(conn, path)

    try:
        _, defeated = enemy.apply_damage(dmg, "magic")
    except Exception as exc:
        logger.error("Nie udało się zadać obrażeń Magic Missle: %s", exc)
        game.ui_log(f"Magic Missle nie powiodło się: {exc}")
        return False

    if defeated:
        try:
            board.remove(enemy_pos)
            try:
                game.enemies.remove(enemy)
            except ValueError:
                pass
        except Exception as exc:
            logger.error("Nie udało się usunąć przeciwnika po Magic Missle: %s", exc)
        enemy.position = None
        logger.info("Przeciwnik pokonany przez Magic Missle.")
        game.ui_log("Przeciwnik pokonany przez Magic Missle.")
    else:
        logger.info("Magic Missle trafia – przeciwnik żyje (HP %s).", getattr(enemy, "hp", "?"))
        game.ui_log(f"Magic Missle trafia – przeciwnik żyje (HP {getattr(enemy, 'hp', '?')}).")

    return True
