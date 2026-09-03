"""Rules derived from persistent Silence spell zones."""

from __future__ import annotations

from typing import Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect

from .spells import grid_distance_feet


def actor_in_silence_zone(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> bool:
    """Return whether an actor currently occupies an active Silence sphere."""

    return any(
        effect.kind == "silence_zone"
        and effect.anchor_position is not None
        and actor.position not in effect.excluded_positions
        and grid_distance_feet(actor.position, effect.anchor_position) <= effect.value
        for effect in active_effects
    )


def verbal_spell_is_blocked(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
    *,
    has_verbal_component: bool,
    ignores_components: bool = False,
) -> bool:
    """Resolve Silence's verbal-component restriction for a concrete caster."""

    return (
        has_verbal_component
        and not ignores_components
        and actor_in_silence_zone(actor, active_effects)
    )


__all__ = ["actor_in_silence_zone", "verbal_spell_is_blocked"]
