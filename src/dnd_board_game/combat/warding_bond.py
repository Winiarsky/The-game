"""Deterministic Warding Bond defenses and linked damage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from dnd_board_game.actors import Actor, DamageAffinityProfile
from dnd_board_game.core.damage_types import DamageType
from dnd_board_game.rules import ActiveEffect, RollModifier, RollModifierType

from .spells import grid_distance_feet


def active_warding_bond(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
    combat_actors: Sequence[Actor],
) -> ActiveEffect | None:
    actors_by_id = {str(candidate.id): candidate for candidate in combat_actors}
    return next(
        (
            effect
            for effect in active_effects
            if effect.actor_id == str(actor.id)
            and effect.kind == "warding_bond"
            and effect.source_actor_id in actors_by_id
            and not actors_by_id[effect.source_actor_id].is_defeated()
            and grid_distance_feet(
                actor.position,
                actors_by_id[effect.source_actor_id].position,
            )
            <= 60
        ),
        None,
    )


def warding_bond_saving_throw_modifiers(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
    combat_actors: Sequence[Actor],
) -> tuple[RollModifier, ...]:
    effect = active_warding_bond(actor, active_effects, combat_actors)
    if effect is None:
        return ()
    return (
        RollModifier(
            "Więź ochronna",
            effect.value,
            RollModifierType.SPELL,
        ),
    )


def warding_bond_affinities(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
    combat_actors: Sequence[Actor],
    base: DamageAffinityProfile,
) -> DamageAffinityProfile:
    if active_warding_bond(actor, active_effects, combat_actors) is None:
        return base
    return DamageAffinityProfile(
        resistances=(*base.resistances, *tuple(DamageType)),
        immunities=base.immunities,
        vulnerabilities=base.vulnerabilities,
    )


@dataclass(frozen=True, slots=True)
class WardingBondTransfer:
    state: object
    source_damage: object | None


def transfer_warding_bond_damage(
    state: object,
    *,
    protected_actor: Actor,
    damage_amount: int,
    active_effects: Sequence[ActiveEffect],
) -> WardingBondTransfer:
    """Deal the protected target's post-resistance damage to the caster."""

    actors = tuple(getattr(state, "actors"))
    effect = active_warding_bond(protected_actor, active_effects, actors)
    if effect is None or damage_amount <= 0:
        return WardingBondTransfer(state, None)
    source = next(
        actor
        for actor in actors
        if str(actor.id) == effect.source_actor_id
    )
    from .damage import DamageComponentInput, apply_damage_result, resolve_damage
    from .session import replace_actor

    applied = apply_damage_result(
        source,
        resolve_damage(
            (
                DamageComponentInput(
                    damage_amount,
                    DamageType.CUSTOM,
                    "Więź ochronna — obrażenia powiązane",
                ),
            )
        ),
    )
    return WardingBondTransfer(
        replace_actor(state, applied.actor_after),
        applied,
    )


__all__ = [
    "WardingBondTransfer",
    "active_warding_bond",
    "transfer_warding_bond_damage",
    "warding_bond_affinities",
    "warding_bond_saving_throw_modifiers",
]
