from __future__ import annotations

import logging

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class EndTurnEvent(GameEvent):
    name = "end"
    default_tags = ["turn", "end"]
    consumes_action = False

    def execute(self, ctx: EventContext) -> EventResult:
        if ctx.in_combat:
            combat = getattr(ctx.game, "state", None)
            active_getter = getattr(combat, "_current_actor", None)
            if callable(active_getter) and ctx.actor is not None:
                try:
                    active = active_getter()
                except Exception:
                    active = None
                if active is not None and active is not ctx.actor:
                    return EventResult(
                        success=False,
                        consumed_action=False,
                        message="To nie jest tura tego aktora.",
                    )
            advance = getattr(combat, "_advance_turn", None)
            if callable(advance):
                advance()
            else:
                logger.info("Brak funkcji advance_turn w stanie walki.")
        # w eksploracji pętla wyboru bohatera sama wróci do promptu
        return EventResult(success=True, consumed_action=self.consumes_action, message="Koniec tury.")
