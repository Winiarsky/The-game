"""Bazowe klasy dla czarów oraz wspólny resolver kontroli kosztów/trybów."""

from __future__ import annotations

import logging

from ..base import EventContext, EventResult, ActionCostEvent
from .magic_utils import grid_distance_feet
from .spell_types import SpellTradition

logger = logging.getLogger(__name__)


class MagicEvent(ActionCostEvent):
    """Bazowa klasa czarów z polami wspólnymi dla większości zaklęć."""

    # w jakich trybach można rzucać
    combat_allowed: bool = True
    hero_turn_allowed: bool = True  # eksploracja / tura bohaterów

    # koszt i znaczniki
    actions_cost: int = 1  # 1-3 akcje
    spell_tags: list[str] | None = None
    spell_tradition: SpellTradition | None = None
    magic_traditions: tuple[SpellTradition, ...] | None = None  # wiele tradycji naraz
    magic_types: list[str] | None = None  # np. szkoła (evocation), cantrip itp.

    # zasięg i UI
    range_feet: int | None = None
    prompt: str | None = None

    def _effective_tags(self, ctx: EventContext) -> list[str]:
        """Połącz tagi bazowe, tagi czaru i tagi z kontekstu."""
        tags: list[str] = []
        if self.default_tags:
            tags.extend(self.default_tags)
        if self.spell_tags:
            tags.extend([t for t in self.spell_tags if t not in tags])
        if ctx.tags:
            tags.extend([t for t in ctx.tags if t not in tags])
        return tags

    # --- helpers ---
    def distance_and_range_ok(self, source: Tuple[int, int], target: Tuple[int, int]) -> tuple[bool, int | None]:
        """Policz dystans i sprawdź limit range_feet (jeśli ustawiony)."""
        distance = grid_distance_feet(source, target)
        if self.range_feet is None:
            return True, distance
        return distance <= self.range_feet, distance


class MagicEventResolver:
    """Waliduje możliwość rzucenia czaru i odpala lifecycle eventu."""

    @staticmethod
    def _has_status(actor, status_id: str) -> bool:
        if actor is None:
            return False
        checker = getattr(actor, "has_status", None)
        if callable(checker):
            try:
                return bool(checker(status_id))
            except Exception:
                return False
        for status in getattr(actor, "statuses", []) or []:
            if getattr(status, "id", status) == status_id:
                return True
        return False

    @staticmethod
    def _remove_status(actor, status_id: str) -> None:
        if actor is None:
            return
        remover = getattr(actor, "remove_status", None)
        if callable(remover):
            try:
                remover(status_id)
                return
            except Exception:
                pass
        statuses = getattr(actor, "statuses", None)
        if not isinstance(statuses, list):
            return
        for idx in range(len(statuses) - 1, -1, -1):
            if getattr(statuses[idx], "id", statuses[idx]) == status_id:
                del statuses[idx]
                return

    @staticmethod
    def resolve(event: MagicEvent, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak aktora rzucającego czar.")

        try:
            cost = int(event.actions_cost)
        except Exception:
            cost = 1
        cost = min(3, max(1, cost))
        event.actions_cost = cost

        # tryb tury
        if ctx.in_combat and not event.combat_allowed:
            msg = f"Czar '{event.name}' niedostępny w walce."
            logger.info(msg)
            return EventResult.cancelled(message=msg)
        if ctx.in_exploration and not event.hero_turn_allowed:
            msg = f"Czar '{event.name}' niedostępny poza walką."
            logger.info(msg)
            return EventResult.cancelled(message=msg)

        reach_applied = False
        if event.range_feet is not None and MagicEventResolver._has_status(actor, "reach_spell_ready"):
            try:
                base_range = int(event.range_feet)
            except Exception:
                base_range = event.range_feet
            tags = {str(tag).strip().lower() for tag in (event.spell_tags or [])}
            is_touch = "touch" in tags
            if isinstance(base_range, int):
                if is_touch and base_range <= 5:
                    event.range_feet = 30
                else:
                    event.range_feet = base_range + 30
                reach_applied = True
                try:
                    game_ui_log = getattr(ctx.game, "ui_log", None)
                    if callable(game_ui_log):
                        game_ui_log(
                            f"Reach Spell: zasieg czaru '{event.name}' zwiekszony z {base_range} ft do {event.range_feet} ft."
                        )
                except Exception:
                    pass

        result = event.run(ctx)
        if result.actions_spent is None and result.consumed_action:
            result.actions_spent = cost
        if reach_applied and result.consumed_action:
            MagicEventResolver._remove_status(actor, "reach_spell_ready")
        return result
