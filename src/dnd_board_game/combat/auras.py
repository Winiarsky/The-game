from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from dnd_board_game.actors import Actor, ActorAura, AuraEffectKind, AuraTarget
from dnd_board_game.rules import RollModifier, RollModifierType

from .spells import grid_distance_feet


@dataclass(frozen=True, slots=True)
class ActiveAura:
    source: Actor
    aura: ActorAura
    affected_actor_ids: tuple[str, ...]


def active_auras(actors: Sequence[Actor]) -> tuple[ActiveAura, ...]:
    result: list[ActiveAura] = []
    for source in actors:
        if source.is_defeated():
            continue
        for aura in source.auras:
            affected = tuple(
                str(target.id)
                for target in actors
                if not target.is_defeated() and actor_is_affected_by_aura(source, target, aura)
            )
            result.append(ActiveAura(source, aura, affected))
    return tuple(result)


def saving_throw_aura_modifiers(
    actors: Sequence[Actor],
    target: Actor,
) -> tuple[RollModifier, ...]:
    return tuple(
        RollModifier(
            active.aura.label,
            active.aura.value,
            RollModifierType.FEATURE,
            stacking_key=f"aura:{active.aura.id}:{active.aura.effect_kind.value}",
        )
        for active in active_auras(actors)
        if active.aura.effect_kind == AuraEffectKind.SAVING_THROW_BONUS
        and str(target.id) in active.affected_actor_ids
    )


def actor_is_affected_by_aura(source: Actor, target: Actor, aura: ActorAura) -> bool:
    if grid_distance_feet(source.position, target.position) > aura.radius_feet:
        return False
    same_actor = source.id == target.id
    same_faction = source.faction == target.faction
    if aura.target == AuraTarget.SELF_AND_ALLIES:
        return same_faction
    if aura.target == AuraTarget.ALLIES:
        return same_faction and not same_actor
    if aura.target == AuraTarget.ENEMIES:
        return not same_faction
    return True
