from __future__ import annotations

import logging
from typing import Optional

from bonuses import BonusEffect, BonusType
from statuses import CoveredStatus
from GameObjects.interactions_mixin import RangeAttackAffectMixin
from GameObjects.items.shield import (
    has_raised_tower_shield_cover,
    tower_shield_cover_owner_key,
)
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


class _RaisedTowerShieldCover(RangeAttackAffectMixin):
    """Tymczasowa osłona reprezentująca aktora z podniesioną tarczą wieżową."""

    cover_type = "standard"

    def __init__(self, owner) -> None:
        self.owner = owner
        self.position = getattr(owner, "position", None)


def _current_actor_ac(actor) -> int | None:
    try:
        from combat import ac_with_bonuses

        return int(ac_with_bonuses(actor)[0] or 0)
    except Exception:
        return None


@register_event
class TakeCoverEvent(GameEvent):
    """Przygarnięcie się do pobliskiej osłony, aby uzyskać lepszą ochronę."""

    name = "cover"
    default_tags = ["take_cover", "defense", "skill"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def _has_raised_shield_bonus(self, hero) -> bool:
        bonuses = getattr(hero, "bonuses", None)
        if not isinstance(bonuses, list):
            return False
        for effect in bonuses:
            source = str(getattr(effect, "source", "") or "")
            if source.startswith("raise_shield:"):
                return True
        return False

    def _can_take_cover_with_tower_shield(self, hero) -> bool:
        return has_raised_tower_shield_cover(hero) and self._has_raised_shield_bonus(hero)

    def _neighbors_with_cover(self, game, pos: tuple[int, int]) -> list[tuple[int, int, RangeAttackAffectMixin]]:
        board = game.board
        result: list[tuple[int, int, RangeAttackAffectMixin]] = []
        for candidate in board.get_neighbors(pos, include_position=True, diagonal=True):
            occupant = board.occupant_at(candidate)
            if has_raised_tower_shield_cover(occupant):
                result.append((candidate[0], candidate[1], _RaisedTowerShieldCover(occupant)))
            elif isinstance(occupant, RangeAttackAffectMixin):
                result.append((candidate[0], candidate[1], occupant))
            for obj in board.interactables_at(candidate):
                if isinstance(obj, RangeAttackAffectMixin):
                    result.append((candidate[0], candidate[1], obj))
            for obj in board.edge_interactables_between(pos, candidate):
                if isinstance(obj, RangeAttackAffectMixin):
                    result.append((candidate[0], candidate[1], obj))
        return result

    def _status_allows_terrain_cover(self, hero, terrain) -> bool:
        if hero is None or terrain is None:
            return False
        terrain_name = getattr(terrain, "name", None)
        terrain_tags = set(getattr(terrain, "terrain_tags", ()) or ())
        for status in getattr(hero, "statuses", []) or []:
            data = getattr(status, "data", None) or {}
            names = data.get("allow_take_cover_terrain_names") or []
            if terrain_name and terrain_name in names:
                return True
            tags = data.get("allow_take_cover_terrain_tags") or []
            if tags and terrain_tags.intersection(tags):
                return True
        return False

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

        cover_obj: RangeAttackAffectMixin | None = None
        current_cover: str | None = None
        using_tower_shield_cover = False
        tower_shield_cover_owner = None
        if not neighbors:
            if self._can_take_cover_with_tower_shield(hero):
                # Tower Shield: Raised + Take Cover daje ochronę jak greater cover (+4 AC).
                current_cover = "standard"
                using_tower_shield_cover = True
                tower_shield_cover_owner = hero
            else:
                terrain = None
                try:
                    terrain = ctx.game.board.cell_at(hero_pos).field
                except Exception:
                    terrain = None
                if terrain is None or not self._status_allows_terrain_cover(hero, terrain):
                    return EventResult.cancelled(message="Brak pobliskiej osłony.")
                cover_obj = terrain if isinstance(terrain, RangeAttackAffectMixin) else None
                if cover_obj is None:
                    return EventResult.cancelled(message="Brak osłony na tym terenie.")

        if cover_obj is None and current_cover is None:
            cover_obj = neighbors[0][2]
        if len(neighbors) > 1 and cover_obj is neighbors[0][2]:
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

        if current_cover is None:
            current_cover = getattr(cover_obj, "range_cover_type", lambda: "standard")()
        if isinstance(cover_obj, _RaisedTowerShieldCover):
            using_tower_shield_cover = True
            tower_shield_cover_owner = getattr(cover_obj, "owner", None)
        upgraded = self._upgrade_cover_type(current_cover)
        if upgraded is None:
            return EventResult.cancelled(message="Osłona już maksymalna (block).")

        # usuń poprzednie efekty tego typu
        remover = getattr(hero, "remove_bonuses_with_prefix", None)
        if callable(remover):
            remover("take_cover:")

        if using_tower_shield_cover:
            if tower_shield_cover_owner is not None:
                source_tag = f"take_cover:tower_shield_from:{tower_shield_cover_owner_key(tower_shield_cover_owner)}"
            else:
                source_tag = "take_cover:tower_shield"
        else:
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
            "Bohater bierze osłonę: %s -> %s (+%d AC circumstance).",
            current_cover,
            upgraded,
            cover_bonus,
        )
        try:
            if using_tower_shield_cover:
                total_ac = _current_actor_ac(hero)
                total_line = f" Razem AC {total_ac}." if total_ac else ""
                ctx.game.ui_log(
                    f"Bierzesz osłonę przy tarczy wieżowej: {current_cover} -> {upgraded} "
                    f"(używa +{cover_bonus} AC zamiast +2 z Raise Shield, bez stackowania).{total_line}"
                )
            else:
                ctx.game.ui_log(
                    f"Bierzesz osłonę: {current_cover} -> {upgraded} (+{cover_bonus} AC circumstance)."
                )
        except Exception:
            pass
        try:
            ui_hero = getattr(ctx.game, "ui_hero", None)
            if callable(ui_hero):
                ui_hero(hero)
        except Exception:
            pass

        return EventResult(success=True, consumed_action=self.consumes_action, message="Bierzesz osłonę.")


def RangeCoverBonusValue(cover_type: str) -> Optional[int]:
    """Zwróć premię do AC dla podanego cover_type."""

    mapping = {"minor": 1, "standard": 2, "greater": 4}
    return mapping.get(cover_type)
