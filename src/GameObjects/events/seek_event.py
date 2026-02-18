from __future__ import annotations

import logging

from board import consts
import GameObjects.interactions_mixin.skill_check_resolver as check_resolver
from ui_client import get_ui_client
from skills import Skill

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class SeekEvent(GameEvent):
    name = "seek"
    default_tags = ["seek", Skill.PERCEPTION.value]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        game = ctx.game
        actor = ctx.actor
        if actor not in getattr(game, "heroes", []) or getattr(actor, "position", None) is None:
            heroes_positions = [hero.position for hero in getattr(game, "heroes", []) if hero.position is not None]
            if not heroes_positions:
                logger.warning("Brak bohaterów na planszy.")
                return EventResult.cancelled(message="Brak bohaterów na planszy.")
            game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
            source = game.conn.scan_board(heroes_positions)
            game.conn.leds_off()
            actor = game.board.occupant_at(source)

        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Nie wybrano bohatera do przeszukania.")

        hero_pos = actor.position
        game.events.safe_emit_action(
            actor=actor,
            action_id="seek_start",
            action_tags=self._effective_tags(ctx),
            pos=hero_pos,
        )

        board = game.board
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
            return EventResult.noop(message="Brak dostępnych pokoi do przeszukania.")

        search_positions = board.positions_in_rooms(set(allowed_rooms)) if allowed_rooms else set()
        search_positions.add(hero_pos)

        base_tags = ["seek", Skill.PERCEPTION.value]
        base_resolution = check_resolver.resolve_skill_check_with_sources(
            skill_id=Skill.PERCEPTION.value,
            dc=consts.SEEK_FAIL,
            actor=actor,
            target=None,
            tags=base_tags,
            game=game,
            apply_modifiers=True,
            consume_statuses=False,
        )
        roll = base_resolution.roll
        roll_total = base_resolution.total

        if rooms_here and roll_total < consts.SEEK_CRITICAL_FAIL:
            for room_id in rooms_here:
                board.lock_room_seek(room_id)
            logger.info("Krytyczna porażka – dalsze przeszukiwanie tych pokoi zablokowane.")
            return EventResult.noop(message="Krytyczna porażka – pokoje zablokowane.")

        newly_revealed_positions: set[tuple[int, int]] = set()
        reveal_notes: list[str] = []
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
                obj_tags = list(getattr(obj, "reveal_tags", ()) or ())
                tags = base_tags + [t for t in obj_tags if t not in base_tags]
                resolution = check_resolver.resolve_skill_check_with_sources_from_roll(
                    skill_id=Skill.PERCEPTION.value,
                    dc=getattr(obj, "reveal_dc", 18),
                    actor=actor,
                    target=obj,
                    tags=tags,
                    roll=roll,
                    game=game,
                    apply_modifiers=True,
                )
                total = resolution.total
                if hasattr(obj, "try_reveal"):
                    obj.try_reveal(total)
                elif total >= getattr(obj, "reveal_dc", 18):
                    obj.revealed = True
                if not was_revealed and getattr(obj, "revealed", False):
                    newly_revealed_positions.add(pos)
                    revealed_count += 1
                    desc = (
                        getattr(obj, "description_on_reveal", None)
                        or getattr(obj, "reveal_description", None)
                        or getattr(obj, "description", None)
                    )
                    if desc:
                        reveal_notes.append(str(desc))
                    logger.info("Odkrywasz %s na polu %s.", obj.__class__.__name__, pos)

        if hidden_candidates == 0:
            logger.info("W wybranych pokojach nie ma ukrytych elementów do przeszukania.")
            return EventResult.noop(message="Brak ukrytych elementów.")
        if not newly_revealed_positions:
            logger.info("Przeszukiwanie niczego nie ujawnia.")
            if rooms_here and roll_total < consts.SEEK_FAIL:
                for room_id in allowed_rooms:
                    board.increment_room_seek_fail(room_id)
                logger.info(
                    "Nieudana próba – pozostałe próby: %s",
                    {room: max(0, consts.SEEK_FAIL_MAX_ATTEMPTS - board.room_seek_failures(room)) for room in allowed_rooms},
                )
            return EventResult.noop(message="Nic nie znaleziono.")

        logger.info("Ujawniono %s ukrytych obiektów w %s polach.", revealed_count, len(newly_revealed_positions))
        game.events.safe_emit_action(
            actor=actor,
            action_id="seek_reveal",
            action_tags=["seek", "reveal"],
            revealed=list(newly_revealed_positions),
            count=revealed_count,
        )
        game.conn.set_leds(list(newly_revealed_positions), consts.HIDDEN_REVEAL_RGB)
        info_text = "Odkryto ukryte obiekty."
        if reveal_notes:
            info_text = "Odkryto:\n" + "\n".join(reveal_notes)
        ui = get_ui_client()
        if ui.enabled:
            ui.prompt_info("Odkryto coś!", prompt_long=info_text, source="seek")
        else:
            time_to_show = getattr(consts, "SEEK_REVEAL_SECONDS", 3)
            try:
                import time

                time.sleep(time_to_show)
            finally:
                pass
        game.conn.leds_off()

        return EventResult(success=True, consumed_action=self.consumes_action, message="Przeszukiwanie wykonane.")
