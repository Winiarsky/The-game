"""Deterministic movement consequences for Spike Growth zones."""

from __future__ import annotations

from typing import Sequence

from dnd_board_game.rules import ActiveEffect
from dnd_board_game.world import Coordinate

from .spells import grid_distance_feet


def spike_growth_damaging_steps(
    path: Sequence[Coordinate],
    active_effects: Sequence[ActiveEffect],
) -> int:
    """Count 5-foot path steps made inside at least one Spike Growth zone."""

    zones = tuple(
        effect
        for effect in active_effects
        if effect.kind == "spike_growth_zone"
        and effect.anchor_position is not None
    )
    return sum(
        1
        for position in path[1:]
        if any(
            position not in zone.excluded_positions
            and grid_distance_feet(position, zone.anchor_position) <= zone.value
            for zone in zones
        )
    )


def spike_growth_damage_dice_count(
    path: Sequence[Coordinate],
    active_effects: Sequence[ActiveEffect],
) -> int:
    """Return the number of d4 rolled: 2d4 for every 5 feet moved in-zone."""

    return spike_growth_damaging_steps(path, active_effects) * 2


__all__ = ["spike_growth_damage_dice_count", "spike_growth_damaging_steps"]
