from __future__ import annotations

import logging

from statuses.race.dwarf.heritages.ancient_blooded import ANCIENT_BLOOD_STATUS
from .base import EventContext, EventResult, GameEvent
from .registry import register_event

logger = logging.getLogger(__name__)


@register_event
class AncientBloodEvent(GameEvent):
    """Akcja: Ancient Blood – aktywuje jednorazowy bonus do save vs magic."""

    name = "ancientblood"
    default_tags = ["dwarf", "ancestry", "ancient_blood"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        hero = ctx.actor
        if hero is None:
            return EventResult.cancelled(message="Brak bohatera do akcji Ancient Blood.")
        if not hasattr(hero, "add_status"):
            return EventResult(success=False, consumed_action=False, message="Bohater nie obsługuje statusów.")
        added = False
        try:
            added = bool(hero.add_status(ANCIENT_BLOOD_STATUS))
        except Exception:
            added = False
        if not added:
            return EventResult(success=False, consumed_action=False, message="Ancient Blood już aktywne.")
        try:
            ctx.game.ui_log("Aktywowano Ancient Blood (+1 do pierwszego rzutu obronnego vs magic).")
        except Exception:
            pass
        return EventResult(success=True, consumed_action=self.consumes_action, message="Ancient Blood aktywne.")
