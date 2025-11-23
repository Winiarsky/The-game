import logging

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

    def _validate_neighbors(self, ctx: ActionContext, neighbours: list[Tuple[int, int]]) -> list[Tuple[int, int]]:
        validated = []
        for neighbor in neighbours:
            _cell = ctx.game.board.cell_at(neighbor)
            if _cell.field.walkable:
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
            while True:
                neighbors = board.get_neighbors(moving_hero.position)
                valid_neighbors = self._validate_neighbors(ctx, neighbors)
                ctx.game.conn.set_leds(valid_neighbors, consts.MOVE_FIELD_RGB)
                target = ctx.game.conn.scan_board(valid_neighbors)
                ctx.game.conn.leds_off()
                moving_hero.set_position(target)
                if target == source and board.occupant_at(target) == None:
                    board.move(source, target)
                    logger.info("Zakończono ruch.")
                    return
                else:
                    continue

