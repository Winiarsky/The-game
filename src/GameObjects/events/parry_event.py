from __future__ import annotations

from bonuses import BonusEffect, BonusType

from .base import EventContext, EventResult, ActionCostEvent
from .registry import register_event
from .weapon_trait_utils import actor_has_equipped_weapon_trait, equipped_weapon_traits


def _first_parry_weapon_id(actor) -> str:
    for weapon, tags in equipped_weapon_traits(actor):
        if "parry" in tags:
            return str(getattr(weapon, "instance_id", "") or getattr(weapon, "item_id", "") or "weapon")
    return "weapon"


@register_event
class ParryEvent(ActionCostEvent):
    """Parry: +1 AC do początku następnej tury."""

    name = "parry"
    default_tags = ["parry"]
    available_in_combat = True
    available_in_exploration = False
    consumes_action = True
    actions_cost = 1

    def execute(self, ctx: EventContext) -> EventResult:
        actor = ctx.actor
        if actor is None:
            return EventResult.cancelled(message="Brak bohatera do akcji parry.")
        if not actor_has_equipped_weapon_trait(actor, "parry"):
            return EventResult.cancelled(message="Parry wymaga aktywnej broni z traitem parry.")

        remover = getattr(actor, "remove_bonuses_with_prefix", None)
        if callable(remover):
            try:
                remover("parry:")
            except Exception:
                pass
        source = f"parry:{_first_parry_weapon_id(actor)}"
        effect = BonusEffect(
            type=BonusType.CIRCUMSTANCE,
            value=1,
            tag="ac",
            source=source,
            label="parry",
            duration_turns=1,
        )
        adder = getattr(actor, "add_bonus", None)
        if callable(adder):
            try:
                adder(effect)
            except Exception:
                pass
        else:
            bonuses = getattr(actor, "bonuses", None)
            if isinstance(bonuses, list):
                bonuses.append(effect)

        try:
            ctx.game.ui_log("Parry: +1 circumstance AC do początku twojej następnej tury.")
        except Exception:
            pass
        return EventResult(
            success=True,
            consumed_action=self.consumes_action,
            actions_spent=self.actions_cost,
            message="Parry aktywne (+1 AC).",
        )
