"""Bazowe klasy dla czarów oraz wspólny resolver kontroli kosztów/trybów."""

from __future__ import annotations

import logging

from ..base import EventContext, EventResult, GameEvent
from .magic_utils import grid_distance_feet
from .spell_types import SpellTradition

logger = logging.getLogger(__name__)


class MagicEvent(GameEvent):
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
    def _actions_remaining(ctx: EventContext, actor) -> int | None:
        combat_state = getattr(ctx.game, "state", None)
        if combat_state is None:
            return None
        try:
            limit = getattr(combat_state, "ACTION_LIMIT", None)
            used = getattr(combat_state, "actions_used", {}).get(actor, 0)
            if limit is None:
                return None
            return int(limit) - int(used)
        except Exception:
            return None

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

        # koszt akcji tylko w walce
        if ctx.in_combat:
            remaining = MagicEventResolver._actions_remaining(ctx, actor)
            if remaining is not None and cost > remaining:
                msg = f"Za mało akcji: potrzebne {cost}, dostępne {remaining}."
                logger.info(msg)
                return EventResult.cancelled(message=msg)

        result = event.run(ctx)
        if result.actions_spent is None and result.consumed_action:
            result.actions_spent = cost
        return result
