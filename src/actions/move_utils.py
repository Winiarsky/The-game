"""Wspólne narzędzia do obsługi pętli ruchu bohatera."""

from __future__ import annotations

import logging
from time import sleep
from typing import Callable, Iterable, Tuple

from board import consts

logger = logging.getLogger(__name__)


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
