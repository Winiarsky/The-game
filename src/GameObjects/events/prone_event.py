from __future__ import annotations

import logging

from statuses import PRONE_STATUS, apply_prone_effects
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class ProneEvent(GameEvent):
    """Położenie się na ziemi – nakłada status prone i związane kary."""

    name = "prone"
    default_tags = ["prone"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Prone dostępne tylko w walce.")

        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak wybranego bohatera do akcji prone.")

        if getattr(hero, "has_status", lambda _s: False)("prone"):
            return EventResult.cancelled(message="Bohater już leży (prone).")

        # nałóż status i kary do ataków
        added = False
        if hasattr(hero, "add_status"):
            try:
                added = hero.add_status(PRONE_STATUS)
            except Exception:
                logger.debug("Nie udało się dodać statusu prone.", exc_info=True)
        apply_prone_effects(hero)

        ctx.game.events.safe_emit_action(
            actor=hero,
            action_id="prone",
            action_tags=self._effective_tags(ctx),
            target=None,
        )

        msg = "Kładziesz się (prone). Ataki wręcz i dystansowe: -2 circumstance."
        logger.info(msg)
        try:
            ctx.game.ui_log(msg)
        except Exception:
            pass

        return EventResult(success=True, consumed_action=self.consumes_action, message=msg if added else None)
