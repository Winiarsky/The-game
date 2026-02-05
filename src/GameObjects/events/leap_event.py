from __future__ import annotations

import logging
from typing import Iterable

from board import consts
from actions.move_utils import _maybe_dispatch_move_reactions
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class LeapEvent(GameEvent):
    """Skok na pole oddalone o 2 – przeskakuje sąsiednie pola, ale respektuje ściany i zajętość lądowiska."""

    name = "leap"
    default_tags = ["move", "leap"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def _candidates(self, board, origin: tuple[int, int]) -> Iterable[tuple[int, int]]:
        ox, oy = origin
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                if dx == 0 and dy == 0:
                    continue
                dist = max(abs(dx), abs(dy))
                if dist != 2:  # tylko pola dokładnie w dystansie 2 (Chebyshev)
                    continue
                pos = (ox + dx, oy + dy)
                if not board.in_bounds(pos):
                    continue
                yield pos

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Leap dostępny tylko w walce.")

        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do akcji leap.")
        origin = getattr(hero, "position", None)
        if origin is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        # zdejmij stealth jak przy ruchu
        try:
            if getattr(hero, "has_status", lambda _s: False)("stealth"):
                hero.remove_status("stealth")
                if hasattr(hero, "stealth_bonus"):
                    hero.stealth_bonus = 0
        except Exception:
            logger.debug("Nie udało się zdjąć stealth przed leap.", exc_info=True)

        board = ctx.game.board

        possible: list[tuple[int, int]] = []
        for pos in self._candidates(board, origin):
            if not board.can_traverse(origin, pos, allow_occupied=False):
                continue
            occupant = board.occupant_at(pos)
            if occupant in getattr(ctx.game, "heroes", []) or occupant in getattr(ctx.game, "enemies", []):
                continue
            possible.append(pos)

        if not possible:
            return EventResult.cancelled(message="Brak dostępnych pól do skoku (2 pola od bohatera).")

        try:
            ctx.game.conn.set_leds(possible, [consts.LEAP_FIELD_RGB] * len(possible))
            choice = ctx.game.conn.scan_board(possible)
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass

        if choice not in possible:
            return EventResult.cancelled(message="Wybrano nieprawidłowe pole do skoku.")

        # sprawdź reakcje na ruch (OA)
        try:
            _maybe_dispatch_move_reactions(ctx, hero, origin, choice)
        except Exception as exc:
            logger.error("Reakcje na leap nie powiodły się: %s", exc)

        try:
            board.move(origin, choice)
        except ValueError as exc:
            return EventResult(success=False, consumed_action=False, message=str(exc))

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="leap",
            action_tags=self._effective_tags(ctx),
            from_pos=origin,
            to_pos=choice,
            leaving_reach=False,
        )

        msg = f"Skok na pole {choice}."
        logger.info(msg)
        try:
            ctx.game.ui_log(msg)
        except Exception:
            pass

        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)
