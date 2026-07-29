"""Board-anchored Zone of Truth save tracking."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Sequence

from dnd_board_game.rules import (
    ActiveEffect,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    SavingThrowResult,
    apply_active_effect,
)
from dnd_board_game.world import Coordinate

from .session import CombatState
from .spells import grid_distance_feet, resolve_spell_save


def zone_of_truth_contains(effect: ActiveEffect, position: Coordinate) -> bool:
    return (
        effect.kind == "zone_of_truth_zone"
        and effect.anchor_position is not None
        and grid_distance_feet(effect.anchor_position, position) <= effect.value
    )


def actor_is_bound_to_truth(
    actor_id: str,
    zone_id: str,
    active_effects: Sequence[ActiveEffect],
) -> bool:
    return any(
        effect.actor_id == actor_id
        and effect.kind == "zone_of_truth_bound"
        and effect.object_id == zone_id
        for effect in active_effects
    )


@dataclass(frozen=True, slots=True)
class ZoneOfTruthSaveResolution:
    active_effects: tuple[ActiveEffect, ...]
    saving_throw: SavingThrowResult | None
    bound: bool


def resolve_zone_of_truth_save(
    state: CombatState,
    active_effects: Sequence[ActiveEffect],
    *,
    actor_id: str,
    zone: ActiveEffect,
    rng: Random,
) -> ZoneOfTruthSaveResolution:
    actor = next(candidate for candidate in state.actors if str(candidate.id) == actor_id)
    current = tuple(active_effects)
    if not zone_of_truth_contains(zone, actor.position):
        return ZoneOfTruthSaveResolution(current, None, False)
    if actor_is_bound_to_truth(actor_id, zone.id, current):
        return ZoneOfTruthSaveResolution(current, None, True)
    caster = next(
        (
            candidate
            for candidate in state.actors
            if str(candidate.id) == zone.source_actor_id
        ),
        None,
    )
    save = resolve_spell_save(
        actor,
        ability="charisma",
        dc=caster.spell_save_dc if caster is not None else 10,
        natural_roll=rng.randint(1, 20),
        condition_states=state.condition_states,
        combat_actors=state.actors,
    )
    if save.success:
        return ZoneOfTruthSaveResolution(current, save, False)
    bound = ActiveEffect(
        id=f"zone-of-truth-bound:{zone.id}:{actor_id}",
        actor_id=actor_id,
        kind="zone_of_truth_bound",
        label="Strefa prawdy — nie może świadomie kłamać",
        object_id=zone.id,
        value=1,
        source_actor_id=zone.source_actor_id,
        target_actor_id=actor_id,
        source=EffectSource(
            EffectSourceType.SPELL,
            "zone_of_truth",
            "Strefa prawdy",
        ),
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
        stacking_key=f"zone-of-truth:{zone.id}:{actor_id}",
        spell_level=2,
    )
    updated = apply_active_effect(current, bound).active_effects
    return ZoneOfTruthSaveResolution(updated, save, True)


def zone_of_truth_zones(
    active_effects: Sequence[ActiveEffect],
) -> tuple[ActiveEffect, ...]:
    return tuple(
        effect
        for effect in active_effects
        if effect.kind == "zone_of_truth_zone"
    )


__all__ = [
    "ZoneOfTruthSaveResolution",
    "actor_is_bound_to_truth",
    "resolve_zone_of_truth_save",
    "zone_of_truth_contains",
    "zone_of_truth_zones",
]
