"""Pure validation of executable v0.3 card modifiers and saved action snapshots."""
from __future__ import annotations

from typing import Any

FLAG_MODIFIERS = frozenset({"check_advantage", "hide_advantage", "no_opportunity", "next_attack_advantage"})
DICE_MODIFIERS = frozenset({"attack_bonus_dice", "damage_dice_extra", "first_damage_dice", "heal_dice", "adjacent_ally_heal_dice"})
NUMBER_MODIFIERS = frozenset({"bonus_move", "self_ac_next_turn", "enemy_save_penalty", "self_temp_hp", "range_bonus",
    "enemy_move_penalty", "perception_penalty", "target_ac_next_turn", "bless_bonus", "target_temp_hp", "heal_flat",
    "move_bonus", "charge_bonus_flat", "shield_pool"})
DAMAGE_TYPES = frozenset({"acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing",
    "poison", "psychic", "radiant", "slashing", "thunder", "magic", "weapon"})


def validate_modifiers(modifiers: Any) -> None:
    """Reject a misspelled or unsupported effect before any player pays for it."""
    if not isinstance(modifiers, dict):
        raise ValueError("Modyfikatory mocy muszą być obiektem.")
    for key, value in modifiers.items():
        if key in FLAG_MODIFIERS:
            valid = value is True
        elif key in NUMBER_MODIFIERS:
            valid = type(value) is int and 0 < value <= 20
        elif key == "hymn_sides":
            valid = type(value) is int and value in {6, 8}
        elif key in DICE_MODIFIERS:
            valid = isinstance(value, list) and 0 < len(value) <= 4
            if valid:
                for part in value:
                    if (not isinstance(part, dict) or type(part.get("count")) is not int or not 1 <= part["count"] <= 6
                            or type(part.get("sides")) is not int or part["sides"] not in {4, 6, 8, 10, 12}
                            or set(part) - {"count", "sides", "damage_type"}):
                        valid = False
                        break
                    if key in {"attack_bonus_dice", "damage_dice_extra", "first_damage_dice"} and part.get("damage_type") not in DAMAGE_TYPES:
                        valid = False
                        break
        else:
            valid = False
        if not valid:
            raise ValueError(f"Nieobsługiwany lub nieprawidłowy modyfikator mocy: {key}.")

