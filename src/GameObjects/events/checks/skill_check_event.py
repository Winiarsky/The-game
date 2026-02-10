"""Elastyczne eventy testów umiejętności oparte na tagach akcji."""

from __future__ import annotations

import logging
from typing import Sequence

from GameObjects.events.base import EventContext, EventResult, GameEvent
from GameObjects.events.registry import register_event
from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources

logger = logging.getLogger(__name__)


class SkillCheckEvent(GameEvent):
    """Bazowy event testu umiejętności sterowany tagami."""

    name: str = "skill_check"
    skill_id: str = "skill"
    skill_label: str = "Umiejętność"
    default_tags: Sequence[str] | None = None
    consumes_action: bool = False  # testy dialogowe nie pochłaniają akcji tury

    def _all_tags(self, ctx: EventContext, skill_id: str) -> list[str]:
        tags = self._effective_tags(ctx)
        if skill_id not in tags:
            tags.append(skill_id)
        return tags

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak aktora do testu umiejętności.")

        dc = ctx.metadata.get("dc") if isinstance(ctx.metadata, dict) else None
        if not isinstance(dc, int):
            return EventResult.cancelled(message="Brak DC dla testu umiejętności.")

        skill_id = ctx.metadata.get("skill_id", self.skill_id) if isinstance(ctx.metadata, dict) else self.skill_id
        skill_label = ctx.metadata.get("skill_label", self.skill_label) if isinstance(ctx.metadata, dict) else self.skill_label

        tags = self._all_tags(ctx, skill_id)

        result = resolve_skill_check_with_sources(
            skill_id=skill_id,
            dc=dc,
            actor=actor,
            target=ctx.metadata.get("target"),
            tags=tags,
            game=ctx.game,
        )

        try:
            ctx.game.events.safe_emit_action(
                actor=actor,
                action_id=skill_id,
                action_tags=tags,
                outcome=result.outcome,
                dc=dc,
                total=result.total,
                roll=result.roll,
                modifier=result.modifier,
                notes=result.notes,
            )
        except Exception:
            logger.debug("safe_emit_action nie powiódł się dla %s", self.skill_id, exc_info=True)

        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            message=f"{skill_label}: {result.outcome}",
            data={
                "outcome": result.outcome,
                "total": result.total,
                "roll": result.roll,
                "modifier": result.modifier,
                "dc": dc,
                "notes": result.notes,
                "skill_id": skill_id,
                "skill_label": skill_label,
            },
        )


@register_event
class GenericSkillCheckEvent(SkillCheckEvent):
    """Jeden punkt wejścia – skill_id w metadata."""

    name = "skill_check"
    skill_id = "skill"
    skill_label = "Umiejętność"
    default_tags = ["skill_check"]
