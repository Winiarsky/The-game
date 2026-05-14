"""Zachowania AI przeciwników."""

from GameObjects.Enemies.behaviors.basic_melee import basic_melee
from GameObjects.Enemies.behaviors.basic_melee_flanking import basic_melee_flanking
from GameObjects.Enemies.behaviors.charred_deacon_guardian import charred_deacon_guardian
from GameObjects.Enemies.behaviors.goblin_commando_raider import goblin_commando_raider
from GameObjects.Enemies.behaviors.goblin_dog_hunter import goblin_dog_hunter
from GameObjects.Enemies.behaviors.goblin_warrior_pack import goblin_warrior_pack

# Prosty rejestr zachowań po identyfikatorze.
_BEHAVIORS = {
    "basic_melee": basic_melee,
    "basic_melee_flanking": basic_melee_flanking,
    "charred_deacon_guardian": charred_deacon_guardian,
    "goblin_warrior_pack": goblin_warrior_pack,
    "goblin_commando_raider": goblin_commando_raider,
    "goblin_dog_hunter": goblin_dog_hunter,
}


def get_behavior(behavior_id: str | None):
    """Zwróć funkcję zachowania po ID, fallback na basic_melee."""
    if behavior_id:
        handler = _BEHAVIORS.get(behavior_id)
        if handler:
            return handler
    return basic_melee


__all__ = [
    "basic_melee",
    "basic_melee_flanking",
    "charred_deacon_guardian",
    "goblin_warrior_pack",
    "goblin_commando_raider",
    "goblin_dog_hunter",
    "get_behavior",
]
