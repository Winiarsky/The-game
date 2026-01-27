import logging
from pathlib import Path
import sys
import time
from typing import Tuple

from .base import ActionContext, BaseAction
from .actions_registy import register
from .move_utils import perform_movement, default_on_enter, find_path, follow_path
from board import consts

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


@register
class MoveAction(BaseAction):
    name = "move"
    prompt_source = "Wybierz bohatera do przesunięcia"
    prompt_target = "Wybierz pole docelowe"
    
    def on_choose_info(self, ctx: ActionContext):
        logger.info("Wybierz bohatera do wykonania akcji ruchu oraz pole docelowe.")

    def _validate_neighbors(self, ctx: ActionContext, current: Tuple[int, int], neighbours: list[Tuple[int, int]]) -> list[Tuple[int, int]]:
        """Zwróć pola, na które można wejść/przejść (plus bieżące pole jako opcja zakończenia).

        allow_occupied=True – można przechodzić przez pola z innymi bohaterami, ale nie kończyć ruchu na nich.
        """
        validated: list[Tuple[int, int]] = [current]
        board = ctx.game.board
        for neighbor in neighbours:
            if neighbor == current:
                continue
            if board.can_traverse(current, neighbor, allow_occupied=True):
                validated.append(neighbor)
        return validated

    def _is_adjacent(self, board, source: Tuple[int, int], target: Tuple[int, int]) -> bool:
        return target in board.get_neighbors(source, include_position=False, diagonal=True)

    def _wait_for_destination(self, ctx: ActionContext, board) -> Tuple[int, int] | None:
        """Czeka na kliknięcie pola na planszy, odrzuca wybory poza planszą."""
        while True:
            target = ctx.game.conn.scan_board(None)
            if board.in_bounds(target):
                return target
            logger.info("Wybrane pole %s jest poza planszą.", target)
            ctx.game.ui_log("Wybrane pole jest poza planszą.")
            ctx.game.conn.leds_off()
            
            
    def execute(self, ctx: ActionContext):
        board = ctx.game.board
        # jeśli mamy wskazanego aktora, użyj go; w przeciwnym razie stary tryb wyboru
        moving_hero = getattr(ctx, "actor", None)
        if moving_hero not in ctx.game.heroes or getattr(moving_hero, "position", None) is None:
            heroes_positions = [hero.position for hero in ctx.game.heroes if hero.position is not None]
            ctx.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)  # niebieskie pola z bohaterami
            source = ctx.game.conn.scan_board(heroes_positions)
            ctx.game.conn.leds_off()
            moving_hero = board.occupant_at(source)

        if moving_hero and moving_hero.position is not None:
            if getattr(moving_hero, "has_status", lambda _s: False)("stealth"):
                moving_hero.remove_status("stealth")  # type: ignore[attr-defined]
                if hasattr(moving_hero, "stealth_bonus"):
                    moving_hero.stealth_bonus = 0
                logger.info("Zdejmuję status stealth – poruszasz się jawnie.")

            started_in_combat = getattr(ctx.game.state, "__class__", None).__name__ == "Combat"

            def _trigger_combat_if_enemy_in_room(pos: tuple[int, int]) -> None:
                if getattr(ctx.game.state, "__class__", None).__name__ == "Combat":
                    return
                rooms_here = board.rooms_at(pos)
                if not rooms_here:
                    return
                for enemy in ctx.game.enemies:
                    if getattr(enemy, "position", None) is None:
                        continue
                    enemy_rooms = board.rooms_at(enemy.position)
                    if rooms_here.intersection(enemy_rooms):
                        logger.info("W pokoju są wrogowie – wywołuję walkę.")
                        try:
                            enemy.trigger_combat(ctx.game)  # type: ignore[attr-defined]
                        except Exception as exc:
                            logger.error("Nie udało się uruchomić walki: %s", exc)
                        break

            # sprawdź startową pozycję przed ruchem
            try:
                _trigger_combat_if_enemy_in_room(moving_hero.position)
            except Exception as exc:
                logger.error("Błąd sprawdzania wrogów w pokoju: %s", exc)

            def _on_enter_wrapper(context, hero_obj, current_pos: tuple[int, int]) -> bool:
                stopped = default_on_enter(context, hero_obj, current_pos)
                try:
                    _trigger_combat_if_enemy_in_room(current_pos)
                except Exception as exc:
                    logger.error("Błąd przy sprawdzaniu walki po wejściu na pole: %s", exc)
                # jeśli w trakcie weszliśmy w combat, zatrzymaj dalszy ruch
                if not started_in_combat and getattr(ctx.game.state, "__class__", None).__name__ == "Combat":
                    return True
                return stopped

            active_path_id: str | None = None
            try:
                while True:
                    target = self._wait_for_destination(ctx, board)
                    if target is None or moving_hero.position is None:
                        if active_path_id:
                            ctx.game.ui_event("path_clear", {"id": active_path_id})
                        return
                    if target == moving_hero.position:
                        logger.info("Kliknięto bieżące pole – kończę akcję ruchu.")
                        if active_path_id:
                            ctx.game.ui_event("path_clear", {"id": active_path_id})
                        return

                    if self._is_adjacent(board, moving_hero.position, target):
                        perform_movement(
                            ctx,
                            moving_hero,
                            moving_hero.position,
                            lambda current: self._validate_neighbors(ctx, current, board.get_neighbors(current)),
                            led_color=consts.MOVE_FIELD_RGB,
                            end_message="Zakończono ruch.",
                            allow_occupied=True,
                            on_enter=_on_enter_wrapper,
                        )
                        if active_path_id:
                            ctx.game.ui_event("path_clear", {"id": active_path_id})
                        return

                    if not board.can_enter(target, allow_occupied=False):
                        logger.info("Pole docelowe %s jest zablokowane lub zajęte.", target)
                        ctx.game.ui_log("Nie możesz stanąć na tym polu.")
                        continue

                    path = find_path(
                        board,
                        moving_hero.position,
                        target,
                        allow_diagonal=True,
                        allow_occupied=True,
                    )
                    if not path or len(path) <= 1:
                        logger.info("Brak możliwej ścieżki do %s.", target)
                        ctx.game.ui_log("Nie da się tam dojść.")
                        continue

                    path_preview = path[1:]
                    steps = len(path_preview)
                    path_id = f"path-{time.time_ns()}"
                    active_path_id = path_id
                    preview_msg = f"Ścieżka do {target}: {steps} pól. Kliknij cel ponownie, aby potwierdzić."
                    ctx.game.ui_event("path_preview", {"id": path_id, "steps": steps, "target": target})
                    logger.info(preview_msg)
                    ctx.game.conn.set_leds(path_preview, consts.MOVE_FIELD_RGB)
                    confirm = ctx.game.conn.scan_board(None)
                    ctx.game.conn.leds_off()

                    if confirm != target:
                        if active_path_id:
                            ctx.game.ui_event("path_clear", {"id": active_path_id})
                            active_path_id = None
                        # potraktuj inne kliknięcie jako zmianę celu i spróbuj ponownie
                        target = confirm
                        if not board.in_bounds(target):
                            ctx.game.ui_log("Wybrane pole jest poza planszą.")
                            logger.info("Kliknięto poza planszą – wybierz ponownie.")
                            continue
                        if target == moving_hero.position:
                            logger.info("Kliknięto bieżące pole – kończę akcję ruchu.")
                            return
                        if self._is_adjacent(board, moving_hero.position, target):
                            perform_movement(
                                ctx,
                                moving_hero,
                                moving_hero.position,
                                lambda current: self._validate_neighbors(ctx, current, board.get_neighbors(current)),
                                led_color=consts.MOVE_FIELD_RGB,
                                end_message="Zakończono ruch.",
                                allow_occupied=True,
                                on_enter=_on_enter_wrapper,
                            )
                            if active_path_id:
                                ctx.game.ui_event("path_clear", {"id": active_path_id})
                            return
                        # w pozostałych przypadkach przejdź do kolejnego obrotu pętli z nowym celem
                        continue

                    completed, stop_pos, reason = follow_path(
                        ctx,
                        moving_hero,
                        path,
                        led_color=consts.MOVE_FIELD_RGB,
                        on_enter=_on_enter_wrapper,
                        allow_occupied=True,
                        step_delay=0.1,
                    )
                    if active_path_id:
                        ctx.game.ui_event("path_clear", {"id": active_path_id})
                        active_path_id = None
                    if completed:
                        logger.info("Zakończono ruch.")
                        return

                    reason_map = {
                        "blocked": "Ruch zatrzymany – ścieżka zablokowana.",
                        "occupied": "Ruch zatrzymany – pole zajęte.",
                        "move_error": "Ruch przerwany przez błąd przesunięcia.",
                        "on_enter": "Ruch zatrzymany przez zdarzenie na polu.",
                    }
                    msg = reason_map.get(reason or "", "Ruch zatrzymany.")
                    ctx.game.ui_log(msg)
                    logger.info(msg)
                    if stop_pos:
                        ctx.game.conn.set_leds([stop_pos], consts.MOVE_FIELD_RGB)
                        # czekaj na kliknięcie pola, na którym zatrzymaliśmy się, aby domknąć akcję
                        ctx.game.conn.scan_board([stop_pos])
                        ctx.game.conn.leds_off()
                    return
            finally:
                ctx.game.conn.leds_off()
