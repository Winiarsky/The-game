from __future__ import annotations

import logging

from statuses.race.goblin.feats.goblin_scuttle import GoblinScuttleStatus
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class GoblinScuttleEvent(GameEvent):
    name = "goblin_scuttle"
    default_tags = ["reaction", "move"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Goblin Scuttle dostępne tylko w walce.")
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do Goblin Scuttle.")

        adder = getattr(actor, "add_status", None)
        if not callable(adder):
            return EventResult.cancelled(message="Bohater nie obsługuje statusów.")

        try:
            adder(GoblinScuttleStatus(duration=1))
        except Exception as exc:
            logger.error("Nie udało się dodać statusu Goblin Scuttle: %s", exc)
            return EventResult.cancelled(message="Nie udało się aktywować Goblin Scuttle.")

        try:
            ctx.game.ui_log("Goblin Scuttle aktywne: zareagujesz Stepem na ruch sojusznika.")
        except Exception:
            pass

        return EventResult(success=True, consumed_action=self.consumes_action, message="Goblin Scuttle aktywne.")
