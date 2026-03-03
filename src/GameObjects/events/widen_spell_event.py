from __future__ import annotations

from statuses.base import Status

from .base import ActionCostEvent, EventContext, EventResult
from .registry import register_event


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
class WidenSpellEvent(ActionCostEvent):
    name = "widen_spell"
    actions_cost = 1
    default_tags = ["manipulate", "metamagic", "spell"]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Widen Spell: brak aktywnego bohatera.")
        if not _has_status(actor, "widen_spell"):
            return EventResult.cancelled(message="Widen Spell: wymaga featu Widen Spell.")

        remover = getattr(actor, "remove_status", None)
        if callable(remover):
            try:
                remover("widen_spell_ready")
            except Exception:
                pass
        status = Status(
            id="widen_spell_ready",
            label="Widen Spell (Ready)",
            duration=1,
            source=self.name,
            data={
                "widen_burst_radius_bonus_feet": 5,
                "widen_short_line_or_cone_bonus_feet": 5,
                "widen_long_line_or_cone_bonus_feet": 10,
            },
        )
        actor.add_status(status)
        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message=(
                "Widen Spell aktywne: nastepny czar obszarowy ma zwiekszony obszar "
                "(na razie rozliczenie reczne per czar)."
            ),
        )
