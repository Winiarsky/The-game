from __future__ import annotations

import logging

from statuses.classes.barbarian.feats.moment_of_clarity import MomentOfClarityStatus
from .base import EventContext, EventResult, ActionCostEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class MomentOfClarityEvent(ActionCostEvent):
    name = "moment_of_clarity"
    default_tags = ["concentrate", "rage"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Moment of Clarity dostępne tylko w walce.")
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do Moment of Clarity.")

        has_status = getattr(actor, "has_status", None)
        if callable(has_status) and not has_status("rage"):
            return EventResult.cancelled(message="Moment of Clarity wymaga aktywnego Rage.")

        adder = getattr(actor, "add_status", None)
        if not callable(adder):
            return EventResult.cancelled(message="Bohater nie obsługuje statusów.")

        try:
            adder(MomentOfClarityStatus(duration=1))
        except Exception as exc:
            logger.error("Nie udało się dodać statusu Moment of Clarity: %s", exc)
            return EventResult.cancelled(message="Nie udało się aktywować Moment of Clarity.")

        try:
            ctx.game.ui_log("Moment of Clarity: możesz używać akcji manipulate do końca tury.")
        except Exception:
            pass

        return EventResult(success=True, consumed_action=self.consumes_action, message="Moment of Clarity aktywne.")
