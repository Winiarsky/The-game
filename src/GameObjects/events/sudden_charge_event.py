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


def _prompt_action_choice(ctx: EventContext, prompt: str, choices: list[str], *, source: str) -> str | None:
    ui = getattr(ctx.game, "ui", None)
    if ui is None or not hasattr(ui, "prompt_choice"):
        return None
    choice_meta = [
        {
            "raw": entry,
            "label": entry,
            "desc": "Zakończ bez ataku." if entry == "end" else "Wykonaj wybraną akcję.",
            "key": str(idx),
        }
        for idx, entry in enumerate(choices, start=1)
    ]
    answer = ui.prompt_choice(
        prompt,
        choices=choices,
        source=source,
        layout="menu_numpad",
        title="Sudden Charge",
        subtitle="Wybierz atak wręcz albo end.",
        choice_meta=choice_meta,
    )
    raw = str(answer or "").strip().lower()
    return raw or None


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

        allowed_melee = sorted(self._allowed_melee_events())
        while True:
            raw_choice = str(
                _prompt_action_choice(
                    ctx,
                    "Sudden Charge - wybierz akcję ataku wręcz",
                    allowed_melee + ["end"],
                    source=self.name,
                )
                or ""
            ).strip().lower()
            if not raw_choice:
                return EventResult.cancelled(message="Sudden Charge: nie wybrano akcji ataku.")

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
