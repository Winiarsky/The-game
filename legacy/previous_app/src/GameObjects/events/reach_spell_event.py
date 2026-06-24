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
class ReachSpellEvent(ActionCostEvent):
    name = "reach_spell"
    actions_cost = 1
    default_tags = ["concentrate", "metamagic", "spell"]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Reach Spell: brak aktywnego bohatera.")
        if not _has_status(actor, "reach_spell"):
            return EventResult.cancelled(message="Reach Spell: wymaga featu Reach Spell.")

        remover = getattr(actor, "remove_status", None)
        if callable(remover):
            try:
                remover("reach_spell_ready")
            except Exception:
                pass
        status = Status(
            id="reach_spell_ready",
            label="Reach Spell (Ready)",
            duration=1,
            source=self.name,
            data={"range_bonus_feet": 30},
        )
        actor.add_status(status)
        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message=(
                "Reach Spell aktywne: nastepny rzucony czar z zasiegiem ma +30 ft "
                "(touch staje sie 30 ft)."
            ),
        )
