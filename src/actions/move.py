import logging
from pathlib import Path
import sys
from typing import Tuple, List, Optional

from hero import Hero
from .base import ActionContext, BaseAction
from .actions_registy import register
from .move_utils import perform_movement, default_on_enter
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
            
            
    def execute(self, ctx: ActionContext):
        heroes_positions = [hero.position for hero in ctx.game.heroes if hero.position is not None]
        ctx.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)  # niebieskie pola z bohaterami
        source = ctx.game.conn.scan_board(heroes_positions)
        ctx.game.conn.leds_off()
        
        board = ctx.game.board
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
