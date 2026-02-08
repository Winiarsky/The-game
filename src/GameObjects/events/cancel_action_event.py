from __future__ import annotations

from .base import EventContext, EventResult, GameEvent
from .registry import register_event


@register_event
class CancelActionEvent(GameEvent):
    name = "cancel"
    default_tags = ["cancel"]
    consumes_action = False

    def execute(self, ctx: EventContext) -> EventResult:
        return EventResult(success=False, consumed_action=False, message="Akcja anulowana.")

