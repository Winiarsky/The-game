from __future__ import annotations

from ....base import EventContext, EventResult
from ....registry import register_event
from ...magic_event import MagicEvent
from ...spell_types import SpellTradition


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


@register_event
class LoremasterEtudeEvent(MagicEvent):
    name = "loremaster_etude"
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "bard", "auditory", "concentrate"]
    spell_tags = ["focus", "occult", "bard"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["focus"]
    prompt = (
        "Loremaster's Etude (Focus): nastepny test Recall Knowledge wykonaj z advantage "
        "(rzuc 2x k20 i wybierz wyzszy wynik). "
        "Aktualnie tylko opis UI - bez automatycznej mechaniki."
    )

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        if not _is_bard(actor):
            return EventResult.cancelled(message="Loremaster's Etude: tylko bard moze rzucic ten czar.")

        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info(
                    "Loremaster's Etude",
                    prompt_long=(
                        "Do kolejnego testu Recall Knowledge rzuc 2x k20 i wybierz wyzszy wynik "
                        "(advantage). Ten event wyswietla tylko przypomnienie UI i nie wymusza mechaniki."
                    ),
                    source="loremaster_etude",
                )
            except Exception:
                pass

        return EventResult(
            success=True,
            consumed_action=ctx.in_combat,
            actions_spent=1 if ctx.in_combat else None,
            message=(
                "Loremaster's Etude: nastepny Recall Knowledge z advantage (2x k20, wybierz wyzszy). "
                "Efekt do rozliczenia recznie."
            ),
        )
