from __future__ import annotations

import logging

from board import consts
from combat import refresh_flanking_statuses
from combat.stealth_runtime import clear_combat_stealth
from statuses import STEALTH_STATUS
from actions.move_utils import (
    _maybe_dispatch_move_reactions,
    consume_difficult_terrain_ignores_for_path,
    find_path,
    movement_budget_feet,
    path_cost_feet,
)

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

    @staticmethod
    def _stance_value(actor, key: str, default=0):
        getter = getattr(actor, "get_status_data", None)
        if callable(getter):
            try:
                return getter("monk_stance_active", key, default)
            except Exception:
                return default
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", None) != "monk_stance_active":
                continue
            data = getattr(status, "data", None) or {}
            return data.get(key, default)
        return default

    def _step_limit_feet(self, hero) -> int:
        limit = 5
        try:
            extra = int(self._stance_value(hero, "step_extra_feet", 0) or 0)
        except Exception:
            extra = 0
        try:
            min_speed = int(self._stance_value(hero, "step_min_speed_feet", 0) or 0)
        except Exception:
            min_speed = 0
        if extra <= 0:
            return limit
        current_speed = movement_budget_feet(hero, default_feet=25)
        if current_speed < max(0, min_speed):
            return limit
        return max(limit, limit + extra)

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
        step_limit_feet = self._step_limit_feet(hero)
        max_squares = max(1, int(step_limit_feet // 5))

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
                clear_combat_stealth(hero, clear_stealth=True, add_observable=True)
        except Exception:
            logger.debug("Nie udało się zdjąć statusu stealth przed stepem.", exc_info=True)

        available_paths: dict[tuple[int, int], list[tuple[int, int]]] = {}
        for dx in range(-max_squares, max_squares + 1):
            for dy in range(-max_squares, max_squares + 1):
                if dx == 0 and dy == 0:
                    continue
                pos = (hero_pos[0] + dx, hero_pos[1] + dy)
                if not board.in_bounds(pos):
                    continue
                occupant = board.occupant_at(pos)
                if occupant in getattr(ctx.game, "heroes", []) or occupant in getattr(ctx.game, "enemies", []):
                    continue
                path = find_path(
                    board,
                    hero_pos,
                    pos,
                    allow_diagonal=True,
                    allow_occupied=False,
                    mover=hero,
                )
                if not path or len(path) <= 1:
                    continue
                if (len(path) - 1) > max_squares:
                    continue
                if path_cost_feet(path, board, mover=hero) > step_limit_feet:
                    continue
                available_paths[pos] = path

        available = list(available_paths.keys())

        if not available:
            return EventResult.cancelled(message="Brak wolnych pól do stepu.")

        positions = [hero_pos] + list(available)
        colors = [consts.MOVE_START_RGB] + [consts.MOVE_FIELD_RGB] * len(available)

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
                ctx.game.ui_log("Wybierz jedno z zaznaczonych pól do stepu.")
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass

        if dest is None:
            return EventResult.cancelled(message="Nie wybrano pola do stepu.")

        start_pos = hero_pos
        path = list(available_paths.get(dest) or [])
        if not path:
            return EventResult.cancelled(message="Nie udało się wyznaczyć ścieżki do stepu.")
        completed, stop_pos, reason = False, start_pos, None
        try:
            from actions.move_utils import follow_path

            completed, stop_pos, reason = follow_path(
                ctx,
                hero,
                path,
                led_color=consts.MOVE_FIELD_RGB,
                allow_occupied=False,
                step_delay=0.0,
            )
        except Exception as exc:
            logger.error("Nie udało się wykonać stepu: %s", exc)
            return EventResult(success=False, consumed_action=False, message=str(exc))

        traversed_path = [start_pos]
        if isinstance(stop_pos, tuple) and stop_pos in path:
            traversed_path = list(path[: path.index(stop_pos) + 1])
        consume_difficult_terrain_ignores_for_path(hero, board, traversed_path)
        if not completed:
            logger.error("Step zatrzymany (%s).", reason)
            return EventResult(success=False, consumed_action=False, message=f"Step zatrzymany ({reason or 'unknown'}).")

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
