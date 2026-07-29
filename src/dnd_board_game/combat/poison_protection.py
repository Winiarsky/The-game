"""Consumers for the Protection from Poison spell."""

from __future__ import annotations

from typing import Sequence

from dnd_board_game.actors import Actor, DamageAffinityProfile
from dnd_board_game.core.damage_types import DamageType
from dnd_board_game.rules import ActiveEffect, RollMode


def has_protection_from_poison(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> bool:
    return any(
        effect.actor_id == str(actor.id)
        and effect.kind == "protection_from_poison"
        for effect in active_effects
    )


def poison_protection_roll_mode(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
    effect_tags: Sequence[str],
    base_mode: RollMode = RollMode.NORMAL,
) -> RollMode:
    if not has_protection_from_poison(actor, active_effects) or not {
        "poison",
        "poisoned",
    }.intersection(effect_tags):
        return base_mode
    if base_mode == RollMode.DISADVANTAGE:
        return RollMode.NORMAL
    return RollMode.ADVANTAGE


def poison_protection_affinities(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> DamageAffinityProfile:
    profile = actor.damage_affinities
    if not has_protection_from_poison(actor, active_effects):
        return profile
    return DamageAffinityProfile(
        resistances=(*profile.resistances, DamageType.POISON),
        immunities=profile.immunities,
        vulnerabilities=profile.vulnerabilities,
    )


__all__ = [
    "has_protection_from_poison",
    "poison_protection_affinities",
    "poison_protection_roll_mode",
]
