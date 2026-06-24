from __future__ import annotations

from statuses.base import Status

from .composition_runtime import get_focus_points, is_bard, set_focus_points

from ....base import EventContext, EventResult
from ....registry import register_event
from ...magic_event import MagicEvent
from ...spell_types import SpellTradition


@register_event
class LoremasterEtudeEvent(MagicEvent):
    name = "loremaster_etude"
    actions_cost = 1
    default_tags = ["magic", "spell", "focus", "bard", "auditory", "concentrate"]
    spell_tags = ["focus", "occult", "bard"]
    magic_traditions = (SpellTradition.OCCULT,)
    magic_types = ["focus"]
    prompt = (
        "Loremaster's Etude (Focus): do konca tej tury nastepny Recall Knowledge "
        "wykonujesz 2x k20 i wybierasz wyzszy wynik."
    )

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do rzucenia czaru.")
        if not is_bard(actor):
            return EventResult.cancelled(message="Loremaster's Etude: tylko bard moze rzucic ten czar.")
        current_focus = get_focus_points(actor)
        if current_focus <= 0:
            return EventResult.cancelled(message="Loremaster's Etude: brak Focus Point.")

        ui = getattr(ctx.game, "ui", None)
        if ui is not None and hasattr(ui, "prompt_info"):
            try:
                ui.prompt_info(
                    "Loremaster's Etude",
                    prompt_long=(
                        "Do kolejnego testu Recall Knowledge przed koncem twojej tury "
                        "rzucasz 2x k20 i wybierasz wyzszy wynik. Efekt rozlicza sie automatycznie."
                    ),
                    source="loremaster_etude",
                )
            except Exception:
                pass

        remover = getattr(actor, "remove_status", None)
        if callable(remover):
            try:
                remover("loremaster_etude_ready")
            except Exception:
                pass
        adder = getattr(actor, "add_status", None)
        if callable(adder):
            try:
                adder(
                    Status(
                        id="loremaster_etude_ready",
                        label="Loremaster's Etude",
                        duration=1,
                        source=self.name,
                        data={"duration_tick_phase": "turn_end", "effect_tags": ["bard", "divination", "knowledge"]},
                    )
                )
            except Exception:
                pass

        set_focus_points(actor, current_focus - 1)
        return EventResult(
            success=True,
            consumed_action=ctx.in_combat,
            actions_spent=1 if ctx.in_combat else None,
            message=(
                "Loremaster's Etude: nastepny Recall Knowledge przed koncem tury "
                f"rzucasz 2x k20 i wybierasz wyzszy wynik. Focus Point: {get_focus_points(actor)}."
            ),
        )
