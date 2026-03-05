from __future__ import annotations

import logging

from board import consts
import GameObjects.interactions_mixin.skill_check_resolver as check_resolver
from ui_client import get_ui_client
from skills import Skill
from GameObjects.events.magic.magic_utils import grid_distance_feet

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class SeekEvent(GameEvent):
    name = "seek"
    default_tags = ["seek", Skill.PERCEPTION.value]
    consumes_action = True

    @staticmethod
    def _seek_radius_feet(actor) -> int:
        base_radius = 30
        if actor is None:
            return base_radius
        has_status = getattr(actor, "has_status", None)
        if callable(has_status):
            try:
                if has_status("deafened"):
                    return base_radius
            except Exception:
                pass
        best = base_radius
        for status in getattr(actor, "statuses", []) or []:
            data = getattr(status, "data", None) or {}
            try:
                radius = int(data.get("seek_sense_radius_feet", 0) or 0)
            except Exception:
                radius = 0
            if radius > best:
                best = radius
        return max(base_radius, best)

    @staticmethod
    def _seek_audio_within_feet(actor) -> int:
        default = 30
        if actor is None:
            return default
        best = default
        for status in getattr(actor, "statuses", []) or []:
            data = getattr(status, "data", None) or {}
            try:
                distance = int(data.get("seek_audio_locate_bonus_within_feet", 0) or 0)
            except Exception:
                distance = 0
            if distance > best:
                best = distance
        return max(default, best)

    @staticmethod
    def _seek_scent_within_feet(actor) -> int:
        default = 0
        if actor is None:
            return default
        best = default
        for status in getattr(actor, "statuses", []) or []:
            data = getattr(status, "data", None) or {}
            try:
                distance = int(data.get("seek_scent_locate_bonus_within_feet", 0) or 0)
            except Exception:
                distance = 0
            if distance > best:
                best = distance
        return max(default, best)

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
        seek_radius = self._seek_radius_feet(actor)
        search_positions = {
            pos for pos in search_positions if grid_distance_feet(hero_pos, pos) <= seek_radius
        }

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
        detected_trap_positions: set[tuple[int, int]] = set()
        reveal_notes: list[str] = []
        trap_notes: list[str] = []
        hidden_candidates = 0
        trap_candidates = 0
        revealed_count = 0
        trap_detected_count = 0

        for pos in search_positions:
            for obj in board.interactables_at(pos):
                is_trap_like = bool(
                    hasattr(obj, "trap_armed")
                    and callable(getattr(obj, "detect_trap", None))
                    and callable(getattr(obj, "disable_trap", None))
                )
                if is_trap_like and bool(getattr(obj, "trap_armed", False)) and not bool(getattr(obj, "trap_detected", False)):
                    trap_candidates += 1
                    trap_tags = base_tags + ["trap", "seek", "search"]
                    trap_resolution = check_resolver.resolve_skill_check_with_sources_from_roll(
                        skill_id=Skill.PERCEPTION.value,
                        dc=int(getattr(obj, "trap_detection_dc", 18) or 18),
                        actor=actor,
                        target=obj,
                        tags=trap_tags,
                        roll=roll,
                        game=game,
                        apply_modifiers=True,
                    )
                    outcome, trap_msg = obj.detect_trap(int(trap_resolution.total or 0))
                    if outcome in ("success", "critical_success"):
                        detected_trap_positions.add(pos)
                        trap_detected_count += 1
                        trap_name = str(getattr(obj, "trap_name", "") or "").strip() or "Pułapka"
                        trap_notes.append(f"{trap_name}: {trap_msg}")
                        logger.info("Wykryto pułapkę %s na polu %s.", trap_name, pos)
                if not getattr(obj, "hidden", False) or getattr(obj, "revealed", False):
                    continue
                if not getattr(obj, "seekable", True):
                    continue
                hidden_candidates += 1
                was_revealed = getattr(obj, "revealed", False)
                obj_tags = list(getattr(obj, "reveal_tags", ()) or ())
                tags = base_tags + [t for t in obj_tags if t not in base_tags]
                if "undetected" not in tags:
                    tags.append("undetected")
                target_distance = grid_distance_feet(hero_pos, pos)
                if target_distance <= 30 and "within_30_feet" not in tags:
                    tags.append("within_30_feet")
                audible = bool(getattr(obj, "audible", False)) or ("auditory" in obj_tags)
                if audible and target_distance <= self._seek_audio_within_feet(actor):
                    if "auditory" not in tags:
                        tags.append("auditory")
                scentable = bool(getattr(obj, "smelly", False)) or bool(getattr(obj, "scentable", False))
                if not scentable:
                    scentable = "scent" in obj_tags or "smelly" in obj_tags
                if scentable and target_distance <= self._seek_scent_within_feet(actor):
                    if "scent" not in tags:
                        tags.append("scent")
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

        if hidden_candidates == 0 and trap_candidates == 0:
            logger.info("W wybranych pokojach nie ma ukrytych elementów ani pułapek do przeszukania.")
            return EventResult.noop(message="Brak ukrytych elementów ani pułapek.")
        if not newly_revealed_positions and not detected_trap_positions:
            logger.info("Przeszukiwanie niczego nie ujawnia.")
            if rooms_here and roll_total < consts.SEEK_FAIL:
                for room_id in allowed_rooms:
                    board.increment_room_seek_fail(room_id)
                logger.info(
                    "Nieudana próba – pozostałe próby: %s",
                    {room: max(0, consts.SEEK_FAIL_MAX_ATTEMPTS - board.room_seek_failures(room)) for room in allowed_rooms},
                )
            return EventResult.noop(message="Nic nie znaleziono.")

        logger.info(
            "Ujawniono %s ukrytych obiektów i wykryto %s pułapek.",
            revealed_count,
            trap_detected_count,
        )
        game.events.safe_emit_action(
            actor=actor,
            action_id="seek_reveal",
            action_tags=["seek", "reveal"],
            revealed=list(newly_revealed_positions),
            count=revealed_count,
            detected_traps=list(detected_trap_positions),
            traps_count=trap_detected_count,
        )
        reveal_positions = list(newly_revealed_positions.union(detected_trap_positions))
        game.conn.set_leds(reveal_positions, consts.HIDDEN_REVEAL_RGB)
        info_text = "Odkryto ukryte obiekty i/lub pułapki."
        if reveal_notes:
            info_text = "Odkryto:\n" + "\n".join(reveal_notes)
        if trap_notes:
            trap_text = "Wykryte pułapki:\n" + "\n".join(trap_notes)
            info_text = f"{info_text}\n{trap_text}" if info_text else trap_text
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
