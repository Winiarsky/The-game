from __future__ import annotations

import logging

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class DelayEvent(GameEvent):
    name = "delay"
    default_tags = ["turn", "delay"]
    consumes_action = False
    available_in_exploration = False
    available_in_combat = True

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult(success=False, consumed_action=False, message="Delay tylko w walce.")
        combat = getattr(ctx.game, "state", None)
        handler = getattr(combat, "_handle_hero_decline", None)
        if callable(handler):
            handler(ctx.actor, auto_delay=True)
            return EventResult(success=True, consumed_action=self.consumes_action, message="Bohater opóźnia turę.")
        logger.info("Brak obsługi delay w stanie walki.")
        return EventResult(success=False, consumed_action=False, message="Delay niedostępny.")
