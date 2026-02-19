from __future__ import annotations

import logging
from typing import Iterable

from board import consts
from actions.move_utils import _maybe_dispatch_move_reactions
from GameObjects.interactions_mixin import LeapBlockerMixin
from statuses import STEALTH_STATUS
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class LeapEvent(GameEvent):
    """Skok na pole oddalone o 2 – przeskakuje sąsiednie pola, ale respektuje ściany i zajętość lądowiska."""

    name = "leap"
    default_tags = ["move", "leap"]
    available_in_combat = True
    available_in_exploration = True
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

    @staticmethod
    def _sign(v: int) -> int:
        return (v > 0) - (v < 0)

    @staticmethod
    def _blocks_leap(obj, origin: tuple[int, int], target: tuple[int, int]) -> bool:
        if not isinstance(obj, LeapBlockerMixin):
            return False
        fn = getattr(obj, "blocks_leap", None)
        if callable(fn):
            try:
                return bool(fn(origin, target))
            except Exception:
                return True
        return True

    def _landing_blockers(self, board, origin: tuple[int, int], target: tuple[int, int]) -> list[LeapBlockerMixin]:
        blockers: list[LeapBlockerMixin] = []
        seen: set[int] = set()

        occupant = board.occupant_at(target)
        if occupant is not None and self._blocks_leap(occupant, origin, target):
            blockers.append(occupant)
            seen.add(id(occupant))

        interactables_at = getattr(board, "interactables_at", None)
        if callable(interactables_at):
            for obj in interactables_at(target):
                if id(obj) in seen:
                    continue
                # tylko obiekty realnie na polu (nie krawędziowe) powinny blokować lądowanie
                pos = getattr(obj, "position", None)
                if pos is not None and pos != target:
                    continue
                if self._blocks_leap(obj, origin, target):
                    blockers.append(obj)
                seen.add(id(obj))

        return blockers

    def _path_clear(self, board, origin: tuple[int, int], target: tuple[int, int]) -> bool:
        """Sprawdź krawędź po krawędzi czy po drodze nie ma ścian ani blokujących obiektów."""
        if board.is_blocked(origin, target):
            return False
        current = origin
        dx = target[0] - origin[0]
        dy = target[1] - origin[1]
        interactables_at = getattr(board, "interactables_at", None)
        while current != target:
            step = (self._sign(dx), self._sign(dy))
            next_pos = (current[0] + step[0], current[1] + step[1])
            if not board.in_bounds(next_pos):
                return False
            if board.is_blocked(current, next_pos):
                return False
            for edge_obj in board.edge_interactables_between(current, next_pos):
                if self._blocks_leap(edge_obj, origin, next_pos):
                    return False
            # środkowe pola nie mogą zawierać obiektów ani LeapBlockerów
            if next_pos != target:
                occupant = board.occupant_at(next_pos)
                if occupant:
                    return False
                if callable(interactables_at):
                    for obj in interactables_at(next_pos):
                        pos = getattr(obj, "position", None)
                        if pos is not None and pos != next_pos:
                            continue
                        if self._blocks_leap(obj, origin, next_pos):
                            return False
            current = next_pos
            dx = target[0] - current[0]
            dy = target[1] - current[1]
        return True

    def execute(self, ctx: EventContext) -> EventResult:

        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do akcji leap.")
        origin = getattr(hero, "position", None)
        if origin is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")
        if getattr(hero, "has_status", lambda _s: False)("grabbed") or getattr(hero, "has_status", lambda _s: False)("restrained"):
            return EventResult.cancelled(message="Nie możesz wykonać leapa będąc grabbed/restrained.")

        try:
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id="leap_start",
                action_tags=self._effective_tags(ctx),
                from_pos=origin,
            )
        except Exception:
            logger.debug("Nie udało się wysłać eventu leap_start.", exc_info=True)

        # zdejmij stealth jak przy ruchu
        try:
            if getattr(hero, "has_status", lambda _s: False)(STEALTH_STATUS):
                hero.remove_status(STEALTH_STATUS)
        except Exception:
            logger.debug("Nie udało się zdjąć stealth przed leap.", exc_info=True)

        board = ctx.game.board

        possible: list[tuple[int, int]] = []
        for pos in self._candidates(board, origin):
            if not board.can_enter(pos, allow_occupied=False):
                continue
            if not self._path_clear(board, origin, pos):
                continue
            occupant = board.occupant_at(pos)
            if occupant in getattr(ctx.game, "heroes", []) or occupant in getattr(ctx.game, "enemies", []):
                continue
            if self._landing_blockers(board, origin, pos):
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
