from __future__ import annotations

from statuses import InspireCourageStatus

from .composition_runtime import composition_blocked, consume_lingering_ready, is_bard, remove_statuses

from ....base import EventContext, EventResult
from ....registry import register_event
from ...magic_event import MagicEvent
from ...magic_utils import grid_distance_feet
from ...spell_types import SpellTradition


@register_event
class InspireCourageEvent(MagicEvent):
    name = "inspire_courage"
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "cantrip", "auditory", "emotion", "inspire"]
    spell_tags = ["cantrip", "focus", "occult", "bard"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["focus", "cantrip"]
    range_feet = 60
    prompt = (
        "Inspire Courage (Focus Cantrip): sojusznicy w 60 ft dostaja +1 status "
        "do testow ataku, +1 do obrazen oraz +1 do save przeciw efektom z tagiem fear. "
        "W walce: 1 akcja. Poza walka: bez kosztu akcji."
    )

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None or getattr(actor, "position", None) is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        if not is_bard(actor):
            return EventResult.cancelled(message="Inspire Courage: tylko bard moze rzucic ten cantrip.")
        if composition_blocked(actor):
            return EventResult.cancelled(
                message="Inspire Courage: po krytycznej porazce Lingering Composition nie mozesz teraz uzywac composition spells."
            )

        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info(
                    "Inspire Courage",
                    prompt_long=(
                        "Sojusznicy w 60 ft otrzymuja +1 status do testow ataku, "
                        "+1 do obrazen i +1 do rzutow obronnych przeciw efektom fear."
                    ),
                    source="inspire_courage",
                )
            except Exception:
                pass

        duration_turns = consume_lingering_ready(actor, default_rounds=1)
        source_id = getattr(actor, "object_id", None) or getattr(actor, "name", None) or str(actor)
        affected = 0
        for hero in getattr(ctx.game, "heroes", []) or []:
            pos = getattr(hero, "position", None)
            if pos is None:
                continue
            if grid_distance_feet(actor.position, pos) > self.range_feet:
                continue
            remove_statuses(hero, "inspire_courage")
            adder = getattr(hero, "add_status", None)
            if not callable(adder):
                continue
            try:
                adder(
                    InspireCourageStatus(
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
            consumed_action=ctx.in_combat,
            actions_spent=1 if ctx.in_combat else None,
            message=f"Inspire Courage: objeci bohaterowie {affected}.{duration_note}",
        )
