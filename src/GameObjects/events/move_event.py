from __future__ import annotations

import logging
import time
from typing import Tuple

from board import consts
from combat import refresh_flanking_statuses
from actions.move_utils import (
    default_on_enter,
    find_path,
    follow_path,
    path_cost_feet,
    perform_movement,
)
from statuses import STEALTH_STATUS

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class MoveEvent(GameEvent):
    name = "move"
    default_tags = ["move"]
    consumes_action = True

    # --- helpers (skopiowane z dawnej MoveAction) ---
    def _validate_neighbors(self, ctx: EventContext, current: Tuple[int, int], neighbours: list[Tuple[int, int]]) -> list[Tuple[int, int]]:
        """Policz pola, na które można wejść/przejść (plus bieżące pole jako opcja zakończenia)."""
        board = ctx.game.board
        validated: list[Tuple[int, int]] = [current]
        for neighbor in neighbours:
            if neighbor == current:
                continue
            if board.can_traverse(current, neighbor, allow_occupied=False):
                validated.append(neighbor)
        return validated

    def _is_adjacent(self, board, source: Tuple[int, int], target: Tuple[int, int]) -> bool:
        return target in board.get_neighbors(source, include_position=False, diagonal=True)

    def _wait_for_destination(self, ctx: EventContext, board) -> Tuple[int, int] | None:
        """Czeka na kliknięcie pola na planszy, odrzuca wybory poza planszą."""
        while True:
            target = ctx.game.conn.scan_board(None)
            if board.in_bounds(target):
                return target
            logger.info("Wybrane pole %s jest poza planszą.", target)
            ctx.game.ui_log("Wybrane pole jest poza planszą.")
            ctx.game.conn.leds_off()

    # --- main flow ---
    def execute(self, ctx: EventContext) -> EventResult:  # noqa: C901
        game = ctx.game
        board = getattr(game, "board", None)
        if board is None:
            return EventResult.cancelled(message="Brak planszy do ruchu.")

        moving_hero = getattr(ctx, "actor", None)
        if moving_hero not in getattr(game, "heroes", []) or getattr(moving_hero, "position", None) is None:
            heroes_positions = [hero.position for hero in getattr(game, "heroes", []) if hero.position is not None]
            if not heroes_positions:
                logger.info("Brak bohaterów na planszy.")
                return EventResult.cancelled(message="Brak bohaterów na planszy.")
            game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
            source = game.conn.scan_board(heroes_positions)
            game.conn.leds_off()
            moving_hero = board.occupant_at(source)

        if moving_hero is None or getattr(moving_hero, "position", None) is None:
            return EventResult.cancelled(message="Nie wybrano bohatera do ruchu.")

        # hint w UI: wybór celu i tworzenie ścieżki
        try:
            game.ui_idle_hint(
                "Wybierz pole docelowe",
                "Kliknij pole, aby utworzyć ścieżkę ruchu.",
            )
        except Exception:
            pass

        # zdejmij stealth przy jawnym ruchu
        if getattr(moving_hero, "has_status", lambda _s: False)(STEALTH_STATUS):
            moving_hero.remove_status(STEALTH_STATUS)  # type: ignore[attr-defined]
            logger.info("Zdejmuję status stealth – poruszasz się jawnie.")

        initial_pos = getattr(moving_hero, "position", None)

        try:
            game.events.safe_emit_action(
                actor=moving_hero,
                action_id="move_start",
                action_tags=self._effective_tags(ctx),
                from_pos=getattr(moving_hero, "position", None),
            )
        except Exception:
            logger.debug("Nie udało się wysłać eventu move_start.", exc_info=True)

        started_in_combat = getattr(game.state, "__class__", None).__name__ == "Combat"

        def _trigger_combat_if_enemy_in_room(pos: tuple[int, int]) -> None:
            if getattr(game.state, "__class__", None).__name__ == "Combat":
                return
            rooms_here = board.rooms_at(pos)
            if not rooms_here:
                return
            for enemy in getattr(game, "enemies", []):
                if getattr(enemy, "position", None) is None:
                    continue
                enemy_rooms = board.rooms_at(enemy.position)
                if rooms_here.intersection(enemy_rooms):
                    logger.info("W pokoju są wrogowie – wywołuję walkę.")
                    try:
                        enemy.trigger_combat(game)  # type: ignore[attr-defined]
                    except Exception as exc:
                        logger.error("Nie udało się uruchomić walki: %s", exc)
                    break

        def _fade_leds(positions: list[tuple[int, int]] | None, colors) -> None:
            """Wygaszanie wzdłuż ścieżki: co krok gasi kolejny LED od startu do celu."""
            nonlocal last_led_positions, last_led_colors
            if not positions:
                try:
                    game.conn.leds_off()
                except Exception:
                    pass
                return
            if isinstance(colors, list) and colors and isinstance(colors[0], list):
                per_pos = [list(map(int, c)) for c in colors]
            else:
                per_pos = [list(map(int, colors)) for _ in positions]  # type: ignore[arg-type]
            try:
                fading = [col[:] for col in per_pos]
                for idx in range(len(positions)):
                    fading[idx] = [0, 0, 0]  # utrzymaj wcześniejsze już wygaszone
                    game.conn.set_leds(positions, fading)
                    time.sleep(0.05)
                game.conn.leds_off()
            except Exception:
                try:
                    game.conn.leds_off()
                except Exception:
                    pass
            last_led_positions = None
            last_led_colors = None

        last_led_positions: list[tuple[int, int]] | None = None
        last_led_colors: list[list[int]] | None = None

        def _set_leds(positions: list[tuple[int, int]], colors) -> None:
            nonlocal last_led_positions, last_led_colors
            game.conn.set_leds(positions, colors)
            if isinstance(colors, list) and colors and isinstance(colors[0], list):
                per_pos = [list(map(int, c)) for c in colors]
            else:
                per_pos = [list(map(int, colors)) for _ in positions]  # type: ignore[arg-type]
            last_led_positions = positions
            last_led_colors = per_pos

        try:
            fade_on_exit = False
            # sprawdź startową pozycję przed ruchem
            try:
                _trigger_combat_if_enemy_in_room(moving_hero.position)
            except Exception as exc:
                logger.error("Błąd sprawdzania wrogów w pokoju: %s", exc)
            if not started_in_combat and getattr(game.state, "__class__", None).__name__ == "Combat":
                logger.info("Walka rozpoczęta podczas wyboru ruchu – kończę akcję.")
                return EventResult(success=True, consumed_action=self.consumes_action, message="Rozpoczęto walkę – ruch zakończony.")

            # natychmiast podświetl pole startowe po wejściu w akcję ruchu
            try:
                _set_leds([moving_hero.position], consts.MOVE_START_RGB)
            except Exception:
                pass

            def _emit_move_event(src_pos: tuple[int, int], dst_pos: tuple[int, int]) -> None:
                game.events.safe_emit_action(
                    actor=moving_hero,
                    action_id="move",
                    action_tags=self._effective_tags(ctx),
                    from_pos=src_pos,
                    to_pos=dst_pos,
                )

            def _on_enter_wrapper(context, hero_obj, current_pos: tuple[int, int]) -> bool:
                stopped = default_on_enter(context, hero_obj, current_pos)
                # sprawdź on_enter na obiektach pola (np. pułapki); zatrzymaj jeśli coś zwróci komunikat
                try:
                    for obj in board.interactables_at(current_pos):
                        on_enter = getattr(obj, "on_enter", None)
                        if callable(on_enter):
                            msg = on_enter(hero_obj, game)
                            if msg:
                                game.ui_log(msg)
                                logger.info("on_enter zatrzymał ruch: %s", msg)
                                stopped = True
                                break
                except Exception as exc:
                    logger.error("Błąd on_enter obiektu na polu %s: %s", current_pos, exc)
                try:
                    _trigger_combat_if_enemy_in_room(current_pos)
                except Exception as exc:
                    logger.error("Błąd przy sprawdzaniu walki po wejściu na pole: %s", exc)
                if not started_in_combat and getattr(game.state, "__class__", None).__name__ == "Combat":
                    return True
                return stopped

            is_prone = getattr(moving_hero, "has_status", lambda _s: False)("prone")
            if is_prone:
                hero_pos = moving_hero.position
                neighbors = board.get_neighbors(hero_pos, include_position=False, diagonal=True)
                available: list[tuple[int, int]] = []
                for pos in neighbors:
                    if not board.can_traverse(hero_pos, pos, allow_occupied=False):
                        continue
                    occupant = board.occupant_at(pos)
                    if occupant in getattr(game, "heroes", []) or occupant in getattr(game, "enemies", []):
                        continue
                    available.append(pos)

                if not available:
                    game.ui_log("Leżąc (prone) nie masz wolnych pól w zasięgu 1.")
                    return EventResult.noop(message="Brak wolnych pól w zasięgu 1.")

                positions = [hero_pos] + available
                colors = [consts.MOVE_START_RGB] + [consts.PRONE_MOVE_RGB] * len(available)
                try:
                    _set_leds(positions, colors)
                    choice = game.conn.scan_board(positions)
                finally:
                    _fade_leds(last_led_positions, last_led_colors)

                if choice == hero_pos:
                    logger.info("Ruch z pozycji prone anulowany.")
                    return EventResult.noop(message="Anulowano ruch z pozycji prone.")
                if choice not in available:
                    game.ui_log("Wybierz jedno z podświetlonych pól obok bohatera.")
                    return EventResult.noop(message="Wybrano nieprawidłowe pole.")

                path = [hero_pos, choice]
                completed, stop_pos, reason = follow_path(
                    ctx,
                    moving_hero,
                    path,
                    led_color=consts.PRONE_MOVE_RGB,
                    on_enter=_on_enter_wrapper,
                    allow_occupied=False,
                    step_delay=0.0,
                )
                if not completed:
                    reason_map = {
                        "blocked": "Ruch zatrzymany – ścieżka zablokowana.",
                        "occupied": "Ruch zatrzymany – pole zajęte.",
                        "move_error": "Ruch przerwany przez błąd przesunięcia.",
                        "on_enter": "Ruch zatrzymany przez zdarzenie na polu.",
                    }
                    msg = reason_map.get(reason or "", "Ruch zatrzymany.")
                    game.ui_log(msg)
                    logger.info(msg)
                    if stop_pos:
                        _set_leds([stop_pos], consts.PRONE_MOVE_RGB)
                    return EventResult.noop(message=msg)

                _emit_move_event(hero_pos, moving_hero.position)
                return EventResult(success=True, consumed_action=self.consumes_action, message="Ruch wykonany.")

            active_path_id: str | None = None
            try:
                while True:
                    target = self._wait_for_destination(ctx, board)
                    if target is None or moving_hero.position is None:
                        if active_path_id:
                            game.ui_event("path_clear", {"id": active_path_id})
                        return EventResult.noop(message="Anulowano ruch.")
                    if target == moving_hero.position:
                        logger.info("Kliknięto bieżące pole – kończę akcję ruchu.")
                        if active_path_id:
                            game.ui_event("path_clear", {"id": active_path_id})
                        return EventResult.noop(message="Ruch bez zmian.")

                    if self._is_adjacent(board, moving_hero.position, target):
                        start_pos = moving_hero.position
                        perform_movement(
                            ctx,
                            moving_hero,
                            moving_hero.position,
                            lambda current: self._validate_neighbors(ctx, current, board.get_neighbors(current)),
                            led_color=consts.MOVE_FIELD_RGB,
                            end_message="Zakończono ruch.",
                            allow_occupied=False,
                            on_enter=_on_enter_wrapper,
                        )
                        _emit_move_event(start_pos, moving_hero.position)
                        if active_path_id:
                            game.ui_event("path_clear", {"id": active_path_id})
                        return EventResult(success=True, consumed_action=self.consumes_action, message="Ruch wykonany.")

                    if not board.can_enter(target, allow_occupied=False):
                        logger.info("Pole docelowe %s jest zablokowane lub zajęte.", target)
                        game.ui_log("Nie możesz stanąć na tym polu.")
                        continue

                    path = find_path(
                        board,
                        moving_hero.position,
                        target,
                        allow_diagonal=True,
                        allow_occupied=False,
                    )
                    if not path or len(path) <= 1:
                        logger.info("Brak możliwej ścieżki do %s.", target)
                        game.ui_log("Nie da się tam dojść.")
                        continue

                    path_preview = path[1:]
                    steps = len(path_preview)
                    feet = path_cost_feet(path)
                    path_id = f"path-{time.time_ns()}"
                    active_path_id = path_id
                    preview_msg = f"Ścieżka do {target}: {steps} pól / {feet} stóp. Kliknij cel ponownie, aby potwierdzić."
                    game.ui_event("path_preview", {"id": path_id, "steps": steps, "feet": feet, "target": target})
                    try:
                        game.ui_idle_hint(
                            "Potwierdź ruch",
                            "Kliknij pole docelowe, aby wykonać ruch lub inne pole, aby ustawić nową ścieżkę.",
                        )
                    except Exception:
                        pass
                    logger.info(preview_msg)
                    leds_positions = [moving_hero.position] + path_preview
                    leds_colors = [consts.MOVE_START_RGB]
                    if path_preview:
                        if len(path_preview) > 1:
                            leds_colors += [consts.MOVE_FIELD_RGB] * (len(path_preview) - 1)
                        leds_colors.append(consts.MOVE_TARGET_RGB)
                    _set_leds(leds_positions, leds_colors)
                    confirm = game.conn.scan_board(None)

                    if confirm != target:
                        if active_path_id:
                            game.ui_event("path_clear", {"id": active_path_id})
                            active_path_id = None
                        last_led_positions = None
                        last_led_colors = None
                        try:
                            game.conn.leds_off()
                        except Exception:
                            pass
                        target = confirm
                        if not board.in_bounds(target):
                            game.ui_log("Wybrane pole jest poza planszą.")
                            logger.info("Kliknięto poza planszą – wybierz ponownie.")
                            continue
                        if target == moving_hero.position:
                            logger.info("Kliknięto bieżące pole – kończę akcję ruchu.")
                            return EventResult.noop(message="Ruch bez zmian.")
                        if self._is_adjacent(board, moving_hero.position, target):
                            start_pos = moving_hero.position
                            perform_movement(
                                ctx,
                                moving_hero,
                                moving_hero.position,
                                lambda current: self._validate_neighbors(ctx, current, board.get_neighbors(current)),
                                led_color=consts.MOVE_FIELD_RGB,
                                end_message="Zakończono ruch.",
                                allow_occupied=False,
                                on_enter=_on_enter_wrapper,
                            )
                            _emit_move_event(start_pos, moving_hero.position)
                            if active_path_id:
                                game.ui_event("path_clear", {"id": active_path_id})
                            return EventResult(success=True, consumed_action=self.consumes_action, message="Ruch wykonany.")
                        continue

                    fade_on_exit = True
                    completed, stop_pos, reason = follow_path(
                        ctx,
                        moving_hero,
                        path,
                        led_color=consts.MOVE_FIELD_RGB,
                        on_enter=_on_enter_wrapper,
                        allow_occupied=False,
                        step_delay=0.1,
                    )
                    if active_path_id:
                        game.ui_event("path_clear", {"id": active_path_id})
                        active_path_id = None
                    if completed:
                        logger.info("Zakończono ruch.")
                        try:
                            _emit_move_event(initial_pos, moving_hero.position)
                        except Exception:
                            logger.debug("Nie udało się wysłać eventu move.", exc_info=True)
                        return EventResult(success=True, consumed_action=self.consumes_action, message="Ruch wykonany.")

                    if (reason == "on_enter") and (not started_in_combat) and getattr(game.state, "__class__", None).__name__ == "Combat":
                        msg = "Rozpoczęto walkę – ruch zakończony."
                        logger.info(msg)
                        return EventResult(success=True, consumed_action=self.consumes_action, message=msg)

                    reason_map = {
                        "blocked": "Ruch zatrzymany – ścieżka zablokowana.",
                        "occupied": "Ruch zatrzymany – pole zajęte.",
                        "move_error": "Ruch przerwany przez błąd przesunięcia.",
                        "on_enter": "Ruch zatrzymany przez zdarzenie na polu.",
                    }
                    msg = reason_map.get(reason or "", "Ruch zatrzymany.")
                    game.ui_log(msg)
                    logger.info(msg)
                    if stop_pos:
                        _set_leds([stop_pos], consts.MOVE_FIELD_RGB)
                    return EventResult.noop(message=msg)
            finally:
                if fade_on_exit:
                    _fade_leds(last_led_positions, last_led_colors)
                else:
                    try:
                        game.conn.leds_off()
                    except Exception:
                        pass
        finally:
            try:
                refresh_flanking_statuses(game)
            except Exception as exc:
                logger.error("Nie udało się odświeżyć flankowania po ruchu: %s", exc)

        return EventResult(success=True, consumed_action=self.consumes_action, message="Ruch wykonany.")
