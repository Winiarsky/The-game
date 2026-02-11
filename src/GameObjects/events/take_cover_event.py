from __future__ import annotations

import logging
from typing import Optional

from bonuses import BonusEffect, BonusType
from statuses import CoveredStatus
from GameObjects.interactions_mixin import RangeAttackAffectMixin
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class TakeCoverEvent(GameEvent):
    """Przygarnięcie się do pobliskiej osłony, aby uzyskać lepszą ochronę."""

    name = "cover"
    default_tags = ["take_cover", "defense", "skill"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def _neighbors_with_cover(self, game, pos: tuple[int, int]) -> list[tuple[int, int, RangeAttackAffectMixin]]:
        board = game.board
        result: list[tuple[int, int, RangeAttackAffectMixin]] = []
        for candidate in board.get_neighbors(pos, include_position=True, diagonal=True):
            occupant = board.occupant_at(candidate)
            if isinstance(occupant, RangeAttackAffectMixin):
                result.append((candidate[0], candidate[1], occupant))
            for obj in board.interactables_at(candidate):
                if isinstance(obj, RangeAttackAffectMixin):
                    result.append((candidate[0], candidate[1], obj))
            for obj in board.edge_interactables_between(pos, candidate):
                if isinstance(obj, RangeAttackAffectMixin):
                    result.append((candidate[0], candidate[1], obj))
        return result

    def _upgrade_cover_type(self, cover_type: str) -> Optional[str]:
        order = ["minor", "standard", "greater", "block"]
        try:
            idx = order.index(cover_type)
        except ValueError:
            return None
        if idx >= len(order) - 1:
            return None  # już block
        return order[idx + 1]

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Take Cover dostępne tylko w walce.")

        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do akcji Take Cover.")
        hero_pos = getattr(hero, "position", None)
        if hero_pos is None:
            return EventResult.cancelled(message="Bohater nie stoi na planszy.")

        neighbors = self._neighbors_with_cover(ctx.game, hero_pos)
        woodland_cover_used = False
        if not neighbors:
            forest_cover = _forest_cover_if_woodland_elf(ctx, hero, hero_pos)
            if forest_cover:
                neighbors = [(hero_pos[0], hero_pos[1], forest_cover)]
                woodland_cover_used = True

        if not neighbors:
            return EventResult.cancelled(message="Brak pobliskiej osłony.")

        cover_obj = neighbors[0][2]
        if len(neighbors) > 1:
            positions = [(x, y) for x, y, _ in neighbors]
            colors = [[60, 140, 60]] * len(positions)
            try:
                ctx.game.conn.set_leds(positions, colors)
            except Exception:
                pass
            try:
                choice = ctx.game.conn.scan_board(positions)
            except Exception:
                choice = None
            finally:
                try:
                    ctx.game.conn.leds_off()
                except Exception:
                    pass
            for x, y, obj in neighbors:
                if (x, y) == choice:
                    cover_obj = obj
                    break
            else:
                return EventResult.cancelled(message="Nie wybrano osłony.")
        current_cover = getattr(cover_obj, "range_cover_type", lambda: "standard")()
        upgraded = self._upgrade_cover_type(current_cover)
        if upgraded is None:
            return EventResult.cancelled(message="Osłona już maksymalna (block).")

        # usuń poprzednie efekty tego typu
        remover = getattr(hero, "remove_bonuses_with_prefix", None)
        if callable(remover):
            remover("take_cover:")

        source_tag = f"take_cover:{hero_pos}"
        adder = getattr(hero, "add_bonus", None)
        if not callable(adder):
            return EventResult(success=False, consumed_action=False, message="Bohater nie obsługuje bonusów.")

        cover_bonus = RangeCoverBonusValue(upgraded)
        if cover_bonus is None:
            return EventResult(success=False, consumed_action=False, message="Nieznany typ osłony.")

        adder(
            BonusEffect(
                type=BonusType.CIRCUMSTANCE,
                value=cover_bonus,
                tag="ac",
                source=source_tag,
                label=f"osłona ({upgraded})",
            )
        )
        # Stealth +2 (circumstance) wynikające z pozycji pod osłoną.
        adder(
            BonusEffect(
                type=BonusType.CIRCUMSTANCE,
                value=2,
                tag="stealth",
                source=source_tag,
                label="osłona (stealth)",
            )
        )

        # status Covered – używany w Stealth
        if hasattr(hero, "add_status"):
            try:
                hero.add_status(CoveredStatus())
            except Exception:
                pass

        logger.info(
            "Bohater bierze osłonę: %s -> %s (+%d AC circumstance).%s",
            current_cover,
            upgraded,
            cover_bonus,
            " (forest)" if woodland_cover_used else "",
        )
        try:
            ctx.game.ui_log(
                f"Bierzesz osłonę: {current_cover} -> {upgraded} (+{cover_bonus} AC circumstance)."
                + (" (Woodland Elf w lesie)" if woodland_cover_used else "")
            )
        except Exception:
            pass

        return EventResult(success=True, consumed_action=self.consumes_action, message="Bierzesz osłonę.")


def RangeCoverBonusValue(cover_type: str) -> Optional[int]:
    """Zwróć premię do AC dla podanego cover_type."""

    mapping = {"minor": 1, "standard": 2, "greater": 4}
    return mapping.get(cover_type)


def _has_status(hero, status_id: str) -> bool:
    checker = getattr(hero, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            pass
    statuses = getattr(hero, "statuses", None)
    if not statuses:
        return False
    for status in statuses:
        if status == status_id:
            return True
        if getattr(status, "id", None) == status_id:
            return True
    return False


def _forest_cover_if_woodland_elf(ctx: EventContext, hero, hero_pos):
    """Zwróć obiekt osłony, jeżeli Woodland Elf stoi na terenie forest."""
    if not _has_status(hero, "heritage_woodland_elf"):
        # alternatywnie respektuj flagę w data
        statuses = getattr(hero, "statuses", None) or []
        if not any(getattr(s, "data", {}).get("forest_take_cover") for s in statuses if hasattr(s, "data")):
            return None

    board = getattr(ctx, "game", None)
    board = getattr(board, "board", None)
    if board is None or not hasattr(board, "cell_at"):
        return None
    try:
        field = board.cell_at(hero_pos).field
    except Exception:
        return None
    terrain_tags = getattr(field, "terrain_tags", ()) or ()
    name = getattr(field, "name", "")
    if "forest" not in terrain_tags and name != "forest":
        return None

    class _ForestCover(RangeAttackAffectMixin):
        cover_type = "standard"
        cover_label = "forest"

    return _ForestCover()
