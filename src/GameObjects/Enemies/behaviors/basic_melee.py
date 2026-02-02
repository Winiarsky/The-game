from __future__ import annotations

import logging
import random

from GameObjects.events import EventContext
from GameObjects.events.registry import dispatch_event
from combat import refresh_flanking_statuses

logger = logging.getLogger(__name__)


def _heroes_in_range(game, enemy_pos: tuple[int, int], include_diagonal: bool = True) -> list[tuple[int, int]]:
    board = game.board
    neighbors = board.get_neighbors(enemy_pos, include_position=False, diagonal=include_diagonal)
    positions: list[tuple[int, int]] = []
    for pos in neighbors:
        occ = board.occupant_at(pos)
        if occ in game.heroes and _adjacent_reachable(board, enemy_pos, pos):
            positions.append(pos)
    return positions


def _nearest_hero(game, enemy_pos: tuple[int, int]) -> tuple[tuple[int, int] | None, int]:
    """Zwraca (pozycja, dystans) najbliższego bohatera (manhattan)."""
    best_pos = None
    best_dist = 999
    for hero in game.heroes:
        if hero.position is None:
            continue
        hx, hy = hero.position
        ex, ey = enemy_pos
        dist = abs(hx - ex) + abs(hy - ey)
        if dist < best_dist:
            best_dist = dist
            best_pos = hero.position
    return best_pos, best_dist


def _adjacent_reachable(board, a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Sprawdza, czy między sąsiadami nie ma ściany/blokera na krawędzi (ignoruje zajętość pól)."""
    if not (board.in_bounds(a) and board.in_bounds(b)):
        return False
    if board.is_blocked(a, b):
        return False
    for edge_obj in board.edge_interactables_between(a, b):
        blocks_passage = getattr(edge_obj, "blocks_passage", None)
        if callable(blocks_passage) and blocks_passage(a, b):
            return False
    return True


def basic_melee(enemy, game, combat_state, actions_left: int = 1) -> int:
    """Bardzo prosty algorytm: ruch (1 akcja) + ewentualnie atak (2 akcje).

    Zwraca liczbę zużytych akcji w tej turze (dla wrógów)."""
    board = game.board
    logger.info("[AI] Start tury wroga %s, pozycja %s, akcje_do_wykorzystania=%s", enemy.name, enemy.position, actions_left)
    if enemy.position is None:
        logger.info("%s nie jest na planszy – pomijam turę.", enemy.name)
        return 0

    actions_used = 0
    attack_cost = 1
    while actions_used < actions_left:
        remaining = actions_left - actions_used
        logger.debug("[AI] Pętla akcji wroga: użyte=%s, pozostalo=%s", actions_used, remaining)
        try:
            refresh_flanking_statuses(game)
        except Exception as exc:
            logger.error("Nie udało się odświeżyć flankowania: %s", exc)
        # próbuj zaatakować, jeśli w zasięgu i masz akcję
        adj = _heroes_in_range(game, enemy.position)
        if adj and remaining >= attack_cost:
            logger.info("[AI] Wróg %s ma cel w zasięgu (%s) – próba ataku przez event.", enemy.name, adj)
            res = dispatch_event("enemy_attack_melee", EventContext(game=game, actor=enemy))
            actions_used += 1 if res.consumed_action else 0
            continue

        if remaining <= 0:
            break

        res = dispatch_event("enemy_move", EventContext(game=game, actor=enemy))
        if res.success:
            actions_used += 1 if res.consumed_action else 0
            continue
        # nieudany ruch też zużywa akcję, by uniknąć pętli
        actions_used += 1
        break

    # jeśli po wszystkich akcjach stoimy obok, informacyjny log
    if _heroes_in_range(game, enemy.position):
        logger.info("%s jest obok bohatera – w kolejnej akcji może zaatakować.", enemy.name)

    return actions_used
