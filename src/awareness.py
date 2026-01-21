"""Helpery czujności strażników oparte na pokojach."""

from __future__ import annotations

import logging
from typing import Iterable, Tuple

logger = logging.getLogger(__name__)


def _is_watchful(obj) -> bool:
    return hasattr(obj, "watch_disabled") and hasattr(obj, "watch_disturbed") and not getattr(obj, "watch_disabled", False)


def iter_watchers_in_rooms(board, rooms: Iterable[str], ignore_obj=None) -> list[tuple[object, tuple[int, int]]]:
    """Zwraca listę (watcher, pozycja) z podanych pokoi, pomija wyłączonych i duplikaty."""
    watchers: list[tuple[object, tuple[int, int]]] = []
    seen: set[int] = set()
    for room_id in rooms or []:
        for pos in board.room_positions.get(room_id, set()):
            try:
                cell = board.cell_at(pos)
            except Exception:
                continue
            occ = getattr(cell, "occupant", None)
            if occ is not None and occ is not ignore_obj and _is_watchful(occ) and id(occ) not in seen:
                seen.add(id(occ))
                watchers.append((occ, pos))
            for obj in getattr(cell, "interactables", []):
                if obj is ignore_obj:
                    continue
                if _is_watchful(obj) and id(obj) not in seen:
                    seen.add(id(obj))
                    watchers.append((obj, pos))
    return watchers


def summarize_watchers(watchers: Iterable[tuple[object, tuple[int, int]]]) -> tuple[int, list[tuple[object, tuple[int, int]]]]:
    """Zwraca (łączna_kara, lista_blokujących_strażników)."""
    penalty = 0
    blockers: list[tuple[object, tuple[int, int]]] = []
    for watcher, pos in watchers:
        if getattr(watcher, "watch_disabled", False):
            continue
        disturbed = getattr(watcher, "watch_disturbed", 0) or 0
        if disturbed <= 0:
            blockers.append((watcher, pos))
        else:
            penalty += disturbed
    return penalty, blockers


def trigger_watchers(game, hero, hero_pos: tuple[int, int]) -> None:
    """Room-based wykrywanie – wywołuje attempt_spot dla strażników w tych samych pokojach."""
    board = game.board
    rooms_here = board.rooms_at(hero_pos)
    watchers = iter_watchers_in_rooms(board, rooms_here, ignore_obj=hero)
    for watcher, _pos in watchers:
        attempt = getattr(watcher, "attempt_spot", None)
        if not callable(attempt):
            continue
        spotted, msg = attempt(hero, game)
        if msg:
            logger.info(msg)
