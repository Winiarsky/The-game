from __future__ import annotations

from .base import ActionCostEvent, EventContext, EventResult
from .demoralize_utils import perform_demoralize
from .registry import register_event


@register_event
class DemoralizeEvent(ActionCostEvent):
    name = "demoralize"
    default_tags = ["concentrate", "emotion", "fear", "mental", "skill", "intimidation"]
    actions_cost = 1
    consumes_action = True
    available_in_combat = True
    available_in_exploration = False

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Demoralize: brak aktora.")
        payload = perform_demoralize(
            ctx,
            actor,
            extra_bonus=0,
            source_action=self.name,
            forced_target=(ctx.metadata or {}).get("forced_target"),
            excluded_target_ids=(ctx.metadata or {}).get("excluded_target_ids"),
            enforce_combat_immunity=True,
        )
        if not bool(payload.get("success", False)):
            return EventResult.cancelled(message=str(payload.get("message") or "Demoralize nieudane."))
        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=self.name,
                action_tags=self._effective_tags(ctx),
                target=payload.get("target"),
                target_pos=payload.get("target_pos"),
                outcome=payload.get("outcome"),
                frightened=payload.get("frightened", 0),
            )
        except Exception:
            pass
        return EventResult(
            success=True,
            consumed_action=True,
            actions_spent=1,
            message=str(payload.get("message") or "Demoralize."),
            data=dict(payload),
        )

