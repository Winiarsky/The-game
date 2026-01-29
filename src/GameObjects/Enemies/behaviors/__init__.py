"""Zachowania AI przeciwników."""

from GameObjects.Enemies.behaviors.basic_melee import basic_melee

# Prosty rejestr zachowań po identyfikatorze.
_BEHAVIORS = {
    "basic_melee": basic_melee,
}


def get_behavior(behavior_id: str | None):
    """Zwróć funkcję zachowania po ID, fallback na basic_melee."""
    if behavior_id:
        handler = _BEHAVIORS.get(behavior_id)
        if handler:
            return handler
    return basic_melee


__all__ = ["basic_melee", "get_behavior"]
