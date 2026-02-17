from __future__ import annotations

import logging

from board import consts
from GameObjects.interactions_mixin.magical_mixin import MagicalMixin

from ..base import EventContext, EventResult
from ..registry import register_event
from .magic_event import MagicEvent
from .magic_utils import grid_distance_feet
from .spell_types import SpellTradition

logger = logging.getLogger(__name__)


def _level_range(actor) -> int:
    try:
        level = int(getattr(actor, "level", 1) or 1)
    except Exception:
        level = 1
    return max(1, level // 2)


def _is_magical(obj) -> bool:
    if obj is None:
        return False
    if getattr(obj, "magical", False):
        return True
    tags = getattr(obj, "tags", None) or []
    return "magical" in tags or "magic" in tags


def _magical_description(obj) -> str:
    desc = getattr(obj, "magical_description", "") or ""
    if desc:
        return desc
    name = getattr(obj, "name", None) or getattr(obj, "label", None)
    if name:
        return f"Magiczny obiekt: {name}"
    return "Magiczna aura."


def _iter_room_objects(ctx: EventContext, rooms: set[str]) -> list[tuple[object, tuple[int, int]]]:
    board = ctx.game.board
    positions = board.positions_in_rooms(rooms) if rooms else set()
    seen: set[int] = set()
    result: list[tuple[object, tuple[int, int]]] = []
    for pos in positions:
        occ = board.occupant_at(pos)
        if occ is not None and id(occ) not in seen:
            seen.add(id(occ))
            result.append((occ, pos))
        for obj in board.interactables_at(pos):
            if id(obj) in seen:
                continue
            seen.add(id(obj))
            result.append((obj, pos))
    return result


@register_event
class DetectMagicEvent(MagicEvent):
    name = "detect_magic"
    default_tags = ["cast", "magic", "detect"]
    consumes_action = True
    actions_cost = 1
    magic_traditions = (
        SpellTradition.ARCANA,
        SpellTradition.DIVINE,
        SpellTradition.OCCULT,
        SpellTradition.PRIMAL,
    )
    prompt = "Detect Magic – wyczuj magiczne aury w pobliżu."

    def execute(self, ctx: EventContext) -> EventResult:
        hero = ctx.actor or self._choose_hero(ctx)
        if hero is None or getattr(hero, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")

        board = ctx.game.board
        hero_pos = hero.position
        rooms_here = board.rooms_at(hero_pos) if hero_pos else set()
        in_room = _iter_room_objects(ctx, rooms_here) if rooms_here else []

        magical_in_room: list[tuple[object, tuple[int, int]]] = [
            (obj, pos) for (obj, pos) in in_room if _is_magical(obj)
        ]

        detect_range_feet = _level_range(hero) * 5
        in_range: list[tuple[object, tuple[int, int]]] = []
        out_of_range_count = 0
        newly_revealed: list[object] = []

        for obj, pos in magical_in_room:
            if hero_pos is None or pos is None:
                out_of_range_count += 1
                continue
            if grid_distance_feet(hero_pos, pos) <= detect_range_feet:
                in_range.append((obj, pos))
                if getattr(obj, "hidden", False) and not getattr(obj, "revealed", False):
                    try:
                        obj.revealed = True
                        newly_revealed.append(obj)
                    except Exception:
                        pass
            else:
                out_of_range_count += 1

        highlight_positions = [
            pos
            for obj, pos in in_range
            if isinstance(obj, MagicalMixin)
            or hasattr(obj, "magical_description")
            or getattr(obj, "magical", False)
        ]

        if highlight_positions:
            try:
                ctx.game.conn.set_leds(
                    highlight_positions,
                    [consts.MAGIC_DETECT_RGB] * len(highlight_positions),
                )
            except Exception:
                pass

        lines: list[str] = []
        if magical_in_room:
            lines.append("Wyczuwasz magię w pomieszczeniu.")
            lines.append(f"Zasięg wykrywania: {detect_range_feet} stóp.")
            if in_range:
                lines.append("Zlokalizowane aury:")
                for obj, _pos in in_range:
                    lines.append(f"- {_magical_description(obj)}")
            if out_of_range_count:
                lines.append(
                    f"Poza zasięgiem wyczuwasz jeszcze {out_of_range_count} magicznych aur."
                )
        else:
            lines.append("Nie wyczuwasz magii w tym pomieszczeniu.")

        if newly_revealed:
            lines.append("Odkryto ukryte magiczne obiekty w zasięgu.")

        info_text = "\n".join(lines)
        try:
            ui = getattr(ctx.game, "ui", None)
            if ui and getattr(ui, "prompt_info", None):
                ui.prompt_info("Detect Magic", prompt_long=info_text, source="detect_magic")
            else:
                ctx.game.ui_log(info_text)
        except Exception:
            pass

        try:
            ctx.game.conn.scan_board(None)
        except Exception:
            pass
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass

        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message="Detect Magic zakończone.",
        )

    def _choose_hero(self, ctx: EventContext):
        heroes_positions = [h.position for h in getattr(ctx.game, "heroes", []) if getattr(h, "position", None) is not None]
        if not heroes_positions:
            logger.info("Brak bohaterów na planszy.")
            return None
        ctx.game.conn.set_leds(heroes_positions, consts.HERO_HIGHLIGHT_RGB)
        try:
            pos = ctx.game.conn.scan_board(heroes_positions)
        finally:
            try:
                ctx.game.conn.leds_off()
            except Exception:
                pass
        return ctx.game.board.occupant_at(pos)


@register_event
class DetectMagicAliasEvent(DetectMagicEvent):
    name = "detectmagic"
