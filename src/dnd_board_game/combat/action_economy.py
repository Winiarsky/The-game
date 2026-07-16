from __future__ import annotations

from enum import StrEnum


class ActionUse(StrEnum):
    ACTION_AVAILABLE = "action_available"
    ACTION_USED = "action_used"


class ActionEconomyCost(StrEnum):
    """A single, explicit turn-economy cost used by combat action providers."""

    ACTION = "action"
    BONUS_ACTION = "bonus_action"
    REACTION = "reaction"
    OBJECT_INTERACTION = "object_interaction"
    FREE = "free"


def action_economy_cost_label(cost: ActionEconomyCost) -> str:
    return {
        ActionEconomyCost.ACTION: "akcja",
        ActionEconomyCost.BONUS_ACTION: "akcja bonusowa",
        ActionEconomyCost.REACTION: "reakcja",
        ActionEconomyCost.OBJECT_INTERACTION: "darmowa interakcja z obiektem lub akcja",
        ActionEconomyCost.FREE: "bez kosztu ekonomii tury",
    }[cost]


def consume_action(state: ActionUse) -> ActionUse:
    if state == ActionUse.ACTION_USED:
        raise ValueError("Action has already been used.")
    return ActionUse.ACTION_USED
