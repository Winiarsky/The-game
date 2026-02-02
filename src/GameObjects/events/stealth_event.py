from __future__ import annotations

import logging

from actions.stealth import StealthAction
from actions.base import ActionContext

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class StealthEvent(GameEvent):
    name = "stealth"
    default_tags = ["stealth", "move"]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        action_ctx = ActionContext(game=ctx.game, heroes_turn=None, actor=ctx.actor, action_tags=self._effective_tags(ctx))
        StealthAction().execute(action_ctx)
        return EventResult(success=True, consumed_action=self.consumes_action, message="Stealth wykonany.")
