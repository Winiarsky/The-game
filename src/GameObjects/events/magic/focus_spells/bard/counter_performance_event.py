from __future__ import annotations

from skills import Skill
from statuses import CounterPerformanceStatus

from GameObjects.interactions_mixin.skill_check_resolver import resolve_skill_check_with_sources

from ....base import EventContext, EventResult
from ....registry import register_event
from ...magic_event import MagicEvent
from ...magic_utils import grid_distance_feet
from ...spell_types import SpellTradition


def _actor_id(actor) -> str | None:
    if actor is None:
        return None
    return getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)


def _is_bard(actor) -> bool:
    has_status = getattr(actor, "has_status", None)
    if callable(has_status):
        try:
            return bool(has_status("bard"))
        except Exception:
            pass
    for status in getattr(actor, "statuses", []) or []:
        if getattr(status, "id", None) == "bard":
            return True
    class_name = str(getattr(actor, "class_name", "") or "").strip().lower()
    return class_name == "bard"

def _remove_statuses(target, status_id: str) -> None:
    statuses = getattr(target, "statuses", None)
    if not isinstance(statuses, list) or not statuses:
        return
    keep = [s for s in statuses if getattr(s, "id", None) != status_id]
    try:
        target.statuses = keep
    except Exception:
        pass


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
        if not _is_bard(actor):
            return EventResult.cancelled(message="Counter Performance: tylko bard moze rzucic ten czar.")

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

        source_id = _actor_id(actor)
        affected = 0

        for hero in getattr(ctx.game, "heroes", []) or []:
            if hero is actor:
                continue
            pos = getattr(hero, "position", None)
            if pos is None:
                continue
            if grid_distance_feet(actor.position, pos) > self.range_feet:
                continue
            _remove_statuses(hero, "counter_performance")
            adder = getattr(hero, "add_status", None)
            if not callable(adder):
                continue
            try:
                adder(
                    CounterPerformanceStatus(
                        performance_total=performance_total,
                        source_id=source_id,
                        source_turns_left=1,
                        source=self.name,
                    )
                )
                affected += 1
            except Exception:
                continue

        return EventResult(
            success=True,
            consumed_action=True,
            message=(
                f"Counter Performance: wynik Performance {performance_total}. "
                f"Objeci sojusznicy: {affected}."
            ),
        )
