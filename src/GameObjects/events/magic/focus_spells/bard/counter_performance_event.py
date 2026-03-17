from __future__ import annotations

from skills import Skill
from statuses import CounterPerformanceStatus

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources
from .composition_runtime import composition_blocked, consume_lingering_ready, is_bard, remove_statuses

from ....base import EventContext, EventResult
from ....registry import register_event
from ...magic_event import MagicEvent
from ...magic_utils import grid_distance_feet
from ...spell_types import SpellTradition


@register_event
class CounterPerformanceEvent(MagicEvent):
    name = "counter_performance"
    actions_cost = 3
    default_tags = ["magic", "spell", "focus", "performance", "auditory"]
    spell_tags = ["focus", "occult", "bard"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["focus"]
    range_feet = 60
    hero_turn_allowed = False
    prompt = (
        "Counter Performance (Bard, Focus Cantrip): Performance check. "
        "Sojusznicy w 60 ft moga uzyc tego wyniku zamiast nizszego Fort/Ref/Will "
        "do poczatku twojej nastepnej tury."
    )

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        if not is_bard(actor):
            return EventResult.cancelled(message="Counter Performance: tylko bard moze rzucic ten czar.")
        if composition_blocked(actor):
            return EventResult.cancelled(
                message="Counter Performance: po krytycznej porazce Lingering Composition nie mozesz teraz uzywac composition spells."
            )

        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info(
                    "Counter Performance",
                    prompt_long=(
                        "Rzucasz Performance. Do poczatku twojej nastepnej tury "
                        "inni bohaterowie w 60 ft moga zastapic nizszy wynik Fort/Ref/Will "
                        "tym wynikiem Performance."
                    ),
                    source="counter_performance",
                )
            except Exception:
                pass

        resolution = resolve_skill_check_with_sources(
            skill_id=Skill.PERFORMANCE.value,
            dc=0,
            actor=actor,
            tags=[Skill.PERFORMANCE.value, "performance", "focus", "counter_performance"],
            game=ctx.game,
            apply_modifiers=True,
        )
        performance_total = int(resolution.total)

        duration_turns = consume_lingering_ready(actor, default_rounds=1)
        source_id = getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)
        affected = 0

        for hero in getattr(ctx.game, "heroes", []) or []:
            if hero is actor:
                continue
            pos = getattr(hero, "position", None)
            if pos is None:
                continue
            if grid_distance_feet(actor.position, pos) > self.range_feet:
                continue
            remove_statuses(hero, "counter_performance")
            adder = getattr(hero, "add_status", None)
            if not callable(adder):
                continue
            try:
                adder(
                    CounterPerformanceStatus(
                        performance_total=performance_total,
                        source_id=source_id,
                        source_turns_left=duration_turns,
                        source=self.name,
                    )
                )
                affected += 1
            except Exception:
                continue

        duration_note = f" Efekt trwa {duration_turns} rundy." if duration_turns > 1 else ""
        return EventResult(
            success=True,
            consumed_action=True,
            message=(
                f"Counter Performance: wynik Performance {performance_total}. "
                f"Objeci sojusznicy: {affected}.{duration_note}"
            ),
        )
