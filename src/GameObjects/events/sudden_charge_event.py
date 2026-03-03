from __future__ import annotations

import logging

from GameObjects.events.move_event import MoveEvent
from GameObjects.events.registry import dispatch_event, list_events
from .base import EventContext, EventResult, ActionCostEvent
from .registry import register_event

logger = logging.getLogger(__name__)


def _has_status(actor, status_id: str) -> bool:
    if actor is None:
        return False
    checker = getattr(actor, "has_status", None)
    if callable(checker):
        try:
            return bool(checker(status_id))
        except Exception:
            return False
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", status) == status_id:
            return True
    return False


@register_event
class SuddenChargeEvent(ActionCostEvent):
    name = "sudden_charge"
    default_tags = ["sudden_charge", "move", "attack_melee", "flourish", "open"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 2

    def _allowed_melee_events(self) -> set[str]:
        all_events = list_events()
        allowed = set()
        for name, cls in all_events.items():
            if not getattr(cls, "available_in_combat", True):
                continue
            tags = list(getattr(cls, "default_tags", []) or [])
            if "attack_melee" in tags or "melee_attack" in tags:
                allowed.add(name)
        return allowed

    def execute(self, ctx: EventContext) -> EventResult:
        if not ctx.in_combat:
            return EventResult.cancelled(message="Sudden Charge dostępne tylko w walce.")
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do Sudden Charge.")
        if not _has_status(actor, "sudden_charge"):
            return EventResult.cancelled(message="Sudden Charge: wymaga featu Sudden Charge.")

        mover = MoveEvent()
        res = mover.execute(ctx)
        if not res.success:
            return EventResult.cancelled(message="Sudden Charge: pierwszy ruch nieudany.")
        res = mover.execute(ctx)
        if not res.success:
            return EventResult.cancelled(message="Sudden Charge: drugi ruch nieudany.")

        try:
            ctx.game.ui_idle_hint(
                "Sudden Charge",
                "Wpisz nazwę akcji ataku wręcz (melee) albo end, aby pominąć atak.",
            )
        except Exception:
            pass

        allowed_melee = self._allowed_melee_events()
        while True:
            raw_choice = ctx.game.conn.read_card("Podaj nazwę akcji").strip().lower()

            if raw_choice == "end":
                return EventResult(
                    success=True,
                    consumed_action=True,
                    actions_spent=self.actions_cost,
                    message="Sudden Charge: atak pominięty.",
                )

            if raw_choice not in allowed_melee:
                try:
                    ctx.game.ui_log("Sudden Charge: odrzucono akcję (dozwolone tylko melee_attack).")
                except Exception:
                    pass
                continue

            attack_result = dispatch_event(raw_choice, EventContext(game=ctx.game, actor=actor))
            msg = attack_result.message or "Sudden Charge: wykonano atak wręcz."
            return EventResult(
                success=True,
                consumed_action=True,
                actions_spent=self.actions_cost,
                message=msg,
            )
