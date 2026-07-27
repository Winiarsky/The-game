from __future__ import annotations

from typing import Any

from .attacks import attack_mechanic_from_source, opportunity_attack_mechanic, ready_attack_mechanic
from .base import ActionMechanic
from .healing import healing_mechanic_from_source
from .movement import basic_move_mechanic, dash_mechanic
from .turn_actions import (
    concentration_attack_bonus_mechanic,
    defensive_spell_reaction_mechanic,
    disengage_mechanic,
    dodge_mechanic,
    help_mechanic,
    long_cast_mechanic,
    ready_mechanic,
    spell_counter_reaction_mechanic,
    spell_movement_mechanic,
    spell_debuff_mechanic,
    spell_dispel_mechanic,
    strength_potion_mechanic,
    summon_mechanic,
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
    if action_type == "reaction_ac_bonus":
        return defensive_spell_reaction_mechanic(
            str(getattr(action, "id", "shield")),
            str(getattr(action, "label", "Czar obronny")),
        )
    if action_type == "spell_counter":
        return spell_counter_reaction_mechanic(
            str(getattr(action, "id", "counterspell")),
            str(getattr(action, "label", "Kontrczar")),
        )
    if action_type == "long_cast_effect":
        return long_cast_mechanic(
            str(getattr(action, "id", "long_cast")),
            str(getattr(action, "label", "Długie rzucanie")),
        )
    if action_type == "summon":
        return summon_mechanic(
            str(getattr(action, "id", "summon")),
            str(getattr(action, "label", "Przywołanie")),
        )
    if action_type == "spell_movement":
        return spell_movement_mechanic(
            str(getattr(action, "id", "spell_movement")),
            str(getattr(action, "label", "Magiczny ruch")),
        )
    if action_type == "spell_debuff":
        return spell_debuff_mechanic(
            str(getattr(action, "id", "spell_debuff")),
            str(getattr(action, "label", "Osłabienie")),
        )
    if action_type == "spell_dispel":
        return spell_dispel_mechanic(
            str(getattr(action, "id", "spell_dispel")),
            str(getattr(action, "label", "Rozproszenie magii")),
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
