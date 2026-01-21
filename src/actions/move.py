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
            perform_movement(
                ctx,
                moving_hero,
                moving_hero.position,
                lambda current: self._validate_neighbors(ctx, current, board.get_neighbors(current)),
                led_color=consts.MOVE_FIELD_RGB,
                end_message="Zakończono ruch.",
                allow_occupied=True,
                on_enter=default_on_enter,
            )
