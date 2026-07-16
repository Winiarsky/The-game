from __future__ import annotations

from typing import Any

from .attacks import attack_mechanic_from_source, opportunity_attack_mechanic, ready_attack_mechanic
from .base import ActionMechanic
from .healing import healing_mechanic_from_source
from .movement import basic_move_mechanic, dash_mechanic
from .turn_actions import (
    concentration_attack_bonus_mechanic,
    disengage_mechanic,
    dodge_mechanic,
    help_mechanic,
    ready_mechanic,
    strength_potion_mechanic,
    targeted_item_effect_mechanic,
)


def builtin_combat_mechanics() -> tuple[ActionMechanic, ...]:
    return (
        basic_move_mechanic(),
        dash_mechanic(),
        dodge_mechanic(),
        disengage_mechanic(),
        help_mechanic(),
        concentration_attack_bonus_mechanic(),
        ready_mechanic(),
        opportunity_attack_mechanic(),
        ready_attack_mechanic(),
        strength_potion_mechanic(),
    )


def combat_action_mechanic_from_definition(action: Any) -> ActionMechanic:
    action_type = str(getattr(action, "action_type", ""))
    if action_type == "strength_potion":
        return strength_potion_mechanic(str(getattr(action, "id", "strength_potion")), str(getattr(action, "label", "Napój siły")))
    if action_type == "concentration_attack_bonus":
        return concentration_attack_bonus_mechanic(
            str(getattr(action, "id", "concentration_attack_bonus")),
            str(getattr(action, "label", "Czar koncentracyjny")),
        )
    if action_type == "targeted_item_effect":
        return targeted_item_effect_mechanic(
            str(getattr(action, "id", "targeted_item_effect")),
            str(getattr(action, "label", "Użyj przedmiotu")),
        )
    raise ValueError(f"Unknown combat action mechanic: {action_type}")


def action_mechanic_payload(mechanic: ActionMechanic) -> dict[str, object]:
    return mechanic.as_payload()


__all__ = [
    "action_mechanic_payload",
    "attack_mechanic_from_source",
    "builtin_combat_mechanics",
    "combat_action_mechanic_from_definition",
    "healing_mechanic_from_source",
]
