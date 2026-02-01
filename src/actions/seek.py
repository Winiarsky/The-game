import logging
from pathlib import Path
import sys
from time import sleep

from .actions_registy import register
from .base import ActionContext, BaseAction
from board import consts
from GameObjects.interactions_mixin import prompt_for_roll

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


logger = logging.getLogger(__name__)


@register
class SeekAction(BaseAction):
    name = "seek"
    prompt_source = "Wybierz bohatera do przeszukania"

    def on_choose_info(self, ctx: ActionContext):
        logger.info("Akcja seek: wybierz bohatera, podaj wynik testu, odsłoń ukryte elementy w jego pokoju.")

    def _choose_hero(self, ctx: ActionContext):
        actor = getattr(ctx, "actor", None)
        if actor in ctx.game.heroes and getattr(actor, "position", None) is not None:
            return actor, getattr(actor, "position", None)
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

    def execute(self, ctx: ActionContext):
        hero, hero_pos = self._choose_hero(ctx)
        if hero is None or hero_pos is None:
            return

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="seek_start",
            action_tags=["seek", "perception"],
            pos=hero_pos,
        )

        roll = prompt_for_roll("Podaj wynik testu Przeszukiwania/Perception: ")
        board = ctx.game.board
        rooms_here = board.rooms_at(hero_pos)

        allowed_rooms: list[str] = []
        for room_id in rooms_here:
            if board.is_room_seek_locked(room_id):
                logger.info("Pokój %s jest zablokowany po krytycznej porażce.", room_id)
                continue
            if board.room_seek_failures(room_id) >= consts.SEEK_FAIL_MAX_ATTEMPTS:
                logger.info("W pokoju %s wyczerpano próby przeszukania.", room_id)
                continue
            allowed_rooms.append(room_id)

        if rooms_here and not allowed_rooms:
            logger.info("Nie możesz już przeszukiwać żadnego z tych pokoi.")
            return

        search_positions = board.positions_in_rooms(set(allowed_rooms)) if allowed_rooms else set()
        search_positions.add(hero_pos)  # zawsze uwzględnij pole bohatera

        if rooms_here and roll < consts.SEEK_CRITICAL_FAIL:
            for room_id in rooms_here:
                board.lock_room_seek(room_id)
            logger.info("Krytyczna porażka – dalsze przeszukiwanie tych pokoi zablokowane.")
            return

        newly_revealed_positions: set[tuple[int, int]] = set()
        hidden_candidates = 0
        revealed_count = 0

        for pos in search_positions:
            for obj in board.interactables_at(pos):
                if not getattr(obj, "hidden", False) or getattr(obj, "revealed", False):
                    continue
                if not getattr(obj, "seekable", True):
                    continue
                hidden_candidates += 1
                was_revealed = getattr(obj, "revealed", False)
                if hasattr(obj, "try_reveal"):
                    obj.try_reveal(roll)
                elif roll >= getattr(obj, "reveal_dc", 18):
                    obj.revealed = True
                if not was_revealed and getattr(obj, "revealed", False):
                    newly_revealed_positions.add(pos)
                    revealed_count += 1
                    logger.info("Odkrywasz %s na polu %s.", obj.__class__.__name__, pos)

        if hidden_candidates == 0:
            logger.info("W wybranych pokojach nie ma ukrytych elementów do przeszukania.")
            return
        if not newly_revealed_positions:
            logger.info("Przeszukiwanie niczego nie ujawnia.")
            if rooms_here and roll < consts.SEEK_FAIL:
                for room_id in allowed_rooms:
                    board.increment_room_seek_fail(room_id)
                logger.info("Nieudana próba – dostępne pozostałe próby w pokojach: %s",
                            {room: max(0, consts.SEEK_FAIL_MAX_ATTEMPTS - board.room_seek_failures(room)) for room in allowed_rooms})
            return

        logger.info("Ujawniono %s ukrytych obiektów w %s polach.", revealed_count, len(newly_revealed_positions))
        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="seek_reveal",
            action_tags=["seek", "reveal"],
            revealed=list(newly_revealed_positions),
            count=revealed_count,
        )
        ctx.game.conn.set_leds(list(newly_revealed_positions), consts.HIDDEN_REVEAL_RGB)
        sleep(getattr(consts, "SEEK_REVEAL_SECONDS", 3))
        ctx.game.conn.leds_off()
