from __future__ import annotations

from skills import Skill

from GameObjects.events.magic.focus_spells.bard.composition_runtime import (
    get_focus_points,
    is_bard,
    set_composition_lock,
    set_focus_points,
    set_lingering_ready,
)
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources

from .base import ActionCostEvent, EventContext, EventResult
from .registry import register_event


@register_event
class LingeringCompositionEvent(ActionCostEvent):
    name = "lingering_composition"
    actions_cost = 1
    default_tags = ["magic", "spell", "composition", "concentrate", "metamagic", "performance"]
    consumes_action = True

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Lingering Composition: brak aktywnego bohatera.")
        if not is_bard(actor) or not getattr(actor, "has_status", lambda *_a, **_k: False)("lingering_composition"):
            return EventResult.cancelled(message="Lingering Composition: wymaga featu Lingering Composition.")

        current_focus = get_focus_points(actor)
        if current_focus <= 0:
            return EventResult.cancelled(message="Lingering Composition: brak Focus Point.")

        resolution = resolve_skill_check_with_sources(
            skill_id=Skill.PERFORMANCE.value,
            dc=15,
            actor=actor,
            tags=[Skill.PERFORMANCE.value, "performance", "composition", "lingering_composition"],
            game=ctx.game,
            apply_modifiers=True,
        )
        outcome = str(getattr(resolution, "outcome", "failure") or "failure")
        set_focus_points(actor, current_focus - 1)

        if outcome == "critical_success":
            set_lingering_ready(actor, rounds=4, source=self.name)
            return EventResult(
                success=True,
                consumed_action=bool(ctx.in_combat),
                actions_spent=1 if ctx.in_combat else None,
                message=(
                    "Lingering Composition: critical success. Nastepny composition cantrip "
                    f"trwa 4 rundy. Focus Point: {get_focus_points(actor)}."
                ),
            )
        if outcome == "success":
            set_lingering_ready(actor, rounds=3, source=self.name)
            return EventResult(
                success=True,
                consumed_action=bool(ctx.in_combat),
                actions_spent=1 if ctx.in_combat else None,
                message=(
                    "Lingering Composition: success. Nastepny composition cantrip "
                    f"trwa 3 rundy. Focus Point: {get_focus_points(actor)}."
                ),
            )
        if outcome == "critical_failure":
            set_composition_lock(actor, source=self.name)
            return EventResult(
                success=True,
                consumed_action=bool(ctx.in_combat),
                actions_spent=1 if ctx.in_combat else None,
                message=(
                    "Lingering Composition: critical failure. Do poczatku nastepnej tury "
                    f"nie mozesz uzywac composition spells. Focus Point: {get_focus_points(actor)}."
                ),
            )
        return EventResult(
            success=True,
            consumed_action=bool(ctx.in_combat),
            actions_spent=1 if ctx.in_combat else None,
            message=(
                "Lingering Composition: failure. Nastepny composition cantrip dziala normalnie. "
                f"Focus Point: {get_focus_points(actor)}."
            ),
        )
