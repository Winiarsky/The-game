from __future__ import annotations

import logging

from board import consts
from combat import refresh_flanking_statuses
from statuses import STEALTH_STATUS
from actions.move_utils import _maybe_dispatch_move_reactions

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class StepEvent(GameEvent):
    """Jednopolowy ruch bez prowokowania reakcji (ataków okazyjnych)."""

    name = "step"
    default_tags = ["step"]
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Step dostępny tylko w walce.")

        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak wybranego bohatera do akcji step.")
        hero_pos = getattr(hero, "position", None)
        if hero_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")
        if getattr(hero, "has_status", lambda _s: False)("grabbed") or getattr(hero, "has_status", lambda _s: False)("restrained"):
            return EventResult.cancelled(message="Nie możesz wykonać stepu będąc grabbed/restrained.")
        if getattr(hero, "has_status", lambda _s: False)("prone"):
            return EventResult.cancelled(message="Nie możesz wykonać stepu będąc prone.")

        board = ctx.game.board

        try:
            ctx.game.events.safe_emit_action(
                actor=hero,
                action_id="step_start",
                action_tags=self._effective_tags(ctx),
                from_pos=hero_pos,
            )
        except Exception:
            logger.debug("Nie udało się wysłać eventu step_start.", exc_info=True)

        # pozbądź się stealth jak przy zwykłym ruchu
        try:
            if getattr(hero, "has_status", lambda _s: False)(STEALTH_STATUS):
                hero.remove_status(STEALTH_STATUS)
        except Exception:
            logger.debug("Nie udało się zdjąć statusu stealth przed stepem.", exc_info=True)

        neighbors = board.get_neighbors(hero_pos, include_position=False, diagonal=True)
        available: list[tuple[int, int]] = []
        enemies: list[tuple[int, int]] = []

        for pos in neighbors:
            occupant = board.occupant_at(pos)
            if occupant in getattr(ctx.game, "heroes", []):
                continue  # nie stajemy na innym bohaterze
            if occupant in getattr(ctx.game, "enemies", []):
                enemies.append(pos)
                continue
            if board.can_traverse(hero_pos, pos, allow_occupied=False):
                available.append(pos)

        if not available:
            return EventResult.cancelled(message="Brak wolnych pól do stepu.")

        positions = list(available) + enemies
        colors = [consts.MOVE_FIELD_RGB] * len(available) + [consts.ENEMY_MOVE_RGB] * len(enemies)

        dest: tuple[int, int] | None = None
        try:
            if positions:
                ctx.game.conn.set_leds(positions, colors)
            while True:
                choice = ctx.game.conn.scan_board(positions)
                if choice == hero_pos:
                    return EventResult.cancelled(message="Step anulowany.")
                if choice in available:
                    dest = choice
                    break
                if choice in enemies:
                    ctx.game.ui_log("Nie możesz wejść na pole z wrogiem.")
                else:
                    ctx.game.ui_log("Wybierz jedno z zaznaczonych pól obok bohatera.")
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass

        if dest is None:
            return EventResult.cancelled(message="Nie wybrano pola do stepu.")

        start_pos = hero_pos
        try:
            board.move(start_pos, dest)
        except ValueError as exc:
            logger.error("Nie udało się przesunąć bohatera w stepu: %s", exc)
            return EventResult(success=False, consumed_action=False, message=str(exc))

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="step",
            action_tags=self._effective_tags(ctx),
            from_pos=start_pos,
            to_pos=dest,
            leaving_reach=False,
        )
        try:
            _maybe_dispatch_move_reactions(ctx, hero, start_pos, dest, action_tags=self._effective_tags(ctx))
        except Exception:
            logger.debug("Nie udało się odpalić reakcji na step.", exc_info=True)

        try:
            refresh_flanking_statuses(ctx.game)
        except Exception as exc:
            logger.error("Nie udało się odświeżyć flankowania po stepu: %s", exc)

        return EventResult(success=True, consumed_action=self.consumes_action, message=f"Step na pole {dest}.")
