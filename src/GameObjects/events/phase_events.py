from __future__ import annotations

import logging

from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


class _PhaseEvent(GameEvent):
    consumes_action = False
    default_tags = ["phase"]

    def execute(self, ctx: EventContext) -> EventResult:
        logger.info(self.message)
        if getattr(ctx.game, "ui_log", None):
            ctx.game.ui_log(self.message)
        return EventResult(success=True, consumed_action=False, message=self.message)


@register_event
class PhaseStartExploration(_PhaseEvent):
    name = "phase_start_exploration"
    available_in_combat = False
    message = "Start fazy eksploracji."


@register_event
class PhaseEndExploration(_PhaseEvent):
    name = "phase_end_exploration"
    available_in_combat = False
    message = "Koniec fazy eksploracji."


@register_event
class PhaseStartCombat(_PhaseEvent):
    name = "phase_start_combat"
    available_in_exploration = False
    message = "Start walki."


@register_event
class PhaseEndCombat(_PhaseEvent):
    name = "phase_end_combat"
    available_in_exploration = False
    message = "Koniec walki."

