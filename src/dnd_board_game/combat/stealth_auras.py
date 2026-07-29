"""Dynamic consumers for magical stealth auras."""

from __future__ import annotations

from typing import Sequence

from dnd_board_game.actors import Actor
from dnd_board_game.rules import ActiveEffect

from .spells import grid_distance_feet


def pass_without_trace_bonus(
    actor: Actor,
    actors: Sequence[Actor],
    active_effects: Sequence[ActiveEffect],
) -> int:
    """Return the strongest Pass without Trace bonus affecting ``actor``."""

    actors_by_id = {str(candidate.id): candidate for candidate in actors}
    return max(
        (
            effect.value
            for effect in active_effects
            if effect.kind == "stealth_bonus_aura"
            and (caster := actors_by_id.get(effect.source_actor_id or effect.actor_id))
            is not None
            and actor.faction == caster.faction
            and grid_distance_feet(caster.position, actor.position) <= 30
        ),
        default=0,
    )


__all__ = ["pass_without_trace_bonus"]
