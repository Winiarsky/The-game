from __future__ import annotations

import logging

from actions.interact import InteractAction
from actions.base import ActionContext

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class InteractionEvent(GameEvent):
    name = "interaction"
    default_tags = ["interaction", "manipulate"]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        action_ctx = ActionContext(game=ctx.game, heroes_turn=None, actor=ctx.actor, action_tags=self._effective_tags(ctx))
        InteractAction().execute(action_ctx)
        return EventResult(success=True, consumed_action=self.consumes_action, message="Interakcja zakończona.")
