from __future__ import annotations

from statuses import InspireCourageStatus

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
        if not _is_bard(actor):
            return EventResult.cancelled(message="Inspire Courage: tylko bard moze rzucic ten cantrip.")

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

        source_id = _actor_id(actor)
        affected = 0
        for hero in getattr(ctx.game, "heroes", []) or []:
            pos = getattr(hero, "position", None)
            if pos is None:
                continue
            if grid_distance_feet(actor.position, pos) > self.range_feet:
                continue
            _remove_statuses(hero, "inspire_courage")
            adder = getattr(hero, "add_status", None)
            if not callable(adder):
                continue
            try:
                adder(
                    InspireCourageStatus(
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
            consumed_action=ctx.in_combat,
            actions_spent=1 if ctx.in_combat else None,
            message=f"Inspire Courage: objeci bohaterowie {affected}.",
        )

