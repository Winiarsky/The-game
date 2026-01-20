import logging
from time import sleep

from hero import Hero
from pathlib import Path
import sys
from .base import ActionContext, BaseAction

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from typing import Tuple, List, Optional
from .actions_registy import register
from board import consts
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
            if "stealth" in getattr(moving_hero, "statuses", []):
                try:
                    moving_hero.statuses.remove("stealth")
                except ValueError:
                    pass
                if hasattr(moving_hero, "stealth_bonus"):
                    moving_hero.stealth_bonus = 0
                logger.info("Zdejmuję status stealth – poruszasz się jawnie.")
            current_pos = moving_hero.position
            source_pos = moving_hero.position
            while True:
                neighbors = board.get_neighbors(current_pos)
                valid_neighbors = self._validate_neighbors(ctx, current_pos, neighbors)
                ctx.game.conn.set_leds(valid_neighbors, consts.MOVE_FIELD_RGB)
                target = ctx.game.conn.scan_board(valid_neighbors)
                ctx.game.conn.leds_off()
                if target == current_pos:
                    logger.info("Zakończono ruch.")
                    return

                if not board.can_traverse(current_pos, target, allow_occupied=True):
                    logger.info("Nie można wejść na to pole.")
                    continue

                occupant = board.occupant_at(target)
                if occupant is not None and occupant is not moving_hero:
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
                # Automatyczne wyzwalacze po wejściu na pole (np. pułapki).
                triggered = False
                for obj in board.interactables_at(current_pos):
                    was_hidden = getattr(obj, "hidden", False) and not getattr(obj, "revealed", False)
                    on_enter = getattr(obj, "on_enter", None)
                    if callable(on_enter):
                        result = on_enter(moving_hero, ctx.game)
                        if result:
                            logger.info(result)
                            triggered = True
                        if was_hidden and getattr(obj, "revealed", False):
                            ctx.game.conn.set_leds([current_pos], consts.HIDDEN_REVEAL_RGB)
                            sleep(consts.RESPONSE_DELAY)
                            ctx.game.conn.leds_off()
                if triggered:
                    logger.info("Ruch zakończony na %s przez zdarzenie na polu.", current_pos)
                    return
