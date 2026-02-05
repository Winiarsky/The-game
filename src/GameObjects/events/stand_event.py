from __future__ import annotations

import logging

from statuses import clear_prone_effects
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class StandEvent(GameEvent):
    """Wstanie z ziemi – usuwa status prone. Posiada tag move (prowokuje OA)."""

    name = "stand"
    default_tags = ["move", "stand"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Stand dostępne tylko w walce.")

        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do akcji stand.")

        if getattr(hero, "has_status", lambda _s: False)("stealth"):
            try:
                hero.remove_status("stealth")
                if hasattr(hero, "stealth_bonus"):
                    hero.stealth_bonus = 0  # type: ignore[attr-defined]
            except Exception:
                logger.debug("Nie udało się zdjąć stealth przy stand.", exc_info=True)

        removed_status = False
        if getattr(hero, "has_status", lambda _s: False)("prone"):
            try:
                removed_status = hero.remove_status("prone")
            except Exception:
                logger.debug("Nie udało się usunąć statusu prone.", exc_info=True)
        clear_prone_effects(hero)

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="stand",
            action_tags=self._effective_tags(ctx),
            from_pos=getattr(hero, "position", None),
            to_pos=getattr(hero, "position", None),
            leaving_reach=False,
        )

        msg = "Wstajesz z pozycji prone."
        logger.info(msg)
        try:
            ctx.game.ui_log(msg)
        except Exception:
            pass

        return EventResult(success=removed_status or True, consumed_action=self.consumes_action, message=msg)
