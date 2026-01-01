import logging
from pathlib import Path
import sys

from .actions_registy import register
from .base import ActionContext, BaseAction
from board import consts

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


logger = logging.getLogger(__name__)


@register
class InteractAction(BaseAction):
    name = "interact"
    prompt_source = "Wybierz bohatera do interakcji"
    prompt_target = "Wybierz obiekt do interakcji"

    def on_choose_info(self, ctx: ActionContext):
        logger.info("Akcja interakcji: wybierz bohatera, potem obiekt w zasięgu.")

    def _choose_hero(self, ctx: ActionContext):
        heroes_positions = [hero.position for hero in ctx.game.heroes if hero.position is not None]
        if not heroes_positions:
            logger.warning("Brak bohaterów na planszy.")
            return None, None
        ctx.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
        source = ctx.game.conn.scan_board(heroes_positions)
        ctx.game.conn.leds_off()
        board = ctx.game.board
        hero = board.occupant_at(source)
        return hero, source

    def _choose_interactable(self, ctx: ActionContext, hero_pos):
        board = ctx.game.board
        candidates = board.get_interactables_in_range(hero_pos, include_position=True, diagonal=True)
        positions = [pos for pos, _objs in candidates]
        if not positions:
            logger.info("Brak obiektów do interakcji w sąsiedztwie.")
            return None
        ctx.game.conn.set_leds(positions, consts.INTERACT_FIELD_RGB)
        target = ctx.game.conn.scan_board(positions)
        ctx.game.conn.leds_off()
        return target

    def execute(self, ctx: ActionContext):
        hero, hero_pos = self._choose_hero(ctx)
        if hero is None or hero_pos is None:
            return

        target = self._choose_interactable(ctx, hero_pos)
        if target is None:
            return

        interactables = ctx.game.board.interactables_at(target)
        if not interactables:
            logger.info("Wybrane pole nie ma obiektu do interakcji.")
            return

        interactable = interactables[0]  # na razie pierwszy z listy
        if not interactable.can_interact(hero, ctx.game):
            logger.info("Nie możesz teraz wejść w interakcję z tym obiektem.")
            return

        message = interactable.interact(hero, ctx.game)
        logger.info(message)
