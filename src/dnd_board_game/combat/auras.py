from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Sequence

from dnd_board_game.actors import Actor, ActorAura, AuraEffectKind, AuraTarget
from dnd_board_game.rules import RollModifier, RollModifierType
from dnd_board_game.rules.effects import ActiveEffect, EffectDuration, EffectStackingPolicy

from .spells import grid_distance_feet


@dataclass(frozen=True, slots=True)
class ActiveAura:
    source: Actor
    aura: ActorAura
    affected_actor_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ActiveSpellAura:
    source: Actor
    effect: ActiveEffect
    affected_actor_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HealingGraceResolution:
    active_effects: tuple[ActiveEffect, ...]
    bonus: int = 0
    die_roll: int = 0
    source_actor_id: str | None = None
    effect_id: str | None = None


SPELL_AURA_SOURCE_KINDS = frozenset(
    {
        "bless_aura_source",
        "divine_care_aura_source",
        "healing_grace_aura_source",
    }
)
SPELL_AURA_MEMBER_KINDS = frozenset(
    {
        "bless_roll_bonus",
        "divine_care_aura_penalty",
        "healing_grace_aura_member",
    }
)


def aura_effect_strength(effect: ActiveEffect) -> tuple[int, int, str, str]:
    """Rank one complete aura variant; radius determines coverage, not power."""
    if effect.kind == "divine_care_aura_penalty":
        damage_penalty = (
            effect.modifier
            if effect.object_id.startswith("shared_combat_action:")
            else effect.value
        )
        power = (abs(effect.value), abs(damage_penalty))
    elif effect.kind in {"healing_grace_aura_source", "healing_grace_aura_member"}:
        sides = effect.die_sides or 8
        # Twice the expected healing avoids floating point and ignores charges.
        power = (sides + 1 + 2 * effect.modifier, sides)
    else:
        power = (effect.value, 0)
    return (*power, effect.source_actor_id or effect.actor_id, effect.id)


def strongest_aura_members(effects: Sequence[ActiveEffect]) -> tuple[ActiveEffect, ...]:
    """Keep one recipient effect per aura kind, preserving distinct abilities.

    Call with derived member effects only. Sources must remain alive so the
    weaker aura can take over when the stronger one expires or moves away.
    """
    members: dict[tuple[str, str], ActiveEffect] = {}
    for effect in effects:
        key = (effect.actor_id, effect.kind)
        previous = members.get(key)
        if previous is None or aura_effect_strength(effect) > aura_effect_strength(previous):
            members[key] = effect
    return tuple(members.values())


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


def active_spell_auras(
    actors: Sequence[Actor],
    active_effects: Sequence[ActiveEffect],
) -> tuple[ActiveSpellAura, ...]:
    actors_by_id = {str(actor.id): actor for actor in actors}
    result: list[ActiveSpellAura] = []
    for effect in active_effects:
        if effect.kind not in SPELL_AURA_SOURCE_KINDS or effect.radius_feet <= 0:
            continue
        source_id = effect.source_actor_id or effect.actor_id
        source = actors_by_id.get(source_id)
        if source is None or source.is_defeated():
            continue
        affected = tuple(
            str(target.id)
            for target in actors
            if _spell_aura_affects(source, target, effect)
        )
        result.append(ActiveSpellAura(source, effect, affected))
    return tuple(result)


def synchronize_spell_aura_effects(
    actors: Sequence[Actor],
    active_effects: Sequence[ActiveEffect],
) -> tuple[ActiveEffect, ...]:
    """Rebuild actor-facing aura statuses from current board positions."""

    retained = tuple(
        effect
        for effect in active_effects
        if effect.kind not in SPELL_AURA_MEMBER_KINDS
    )
    members: list[ActiveEffect] = []
    for active in active_spell_auras(actors, retained):
        source_effect = active.effect
        for actor_id in active.affected_actor_ids:
            if source_effect.kind == "bless_aura_source":
                kind = "bless_roll_bonus"
                value = source_effect.die_sides or source_effect.value or 4
            elif source_effect.kind == "divine_care_aura_source":
                kind = "divine_care_aura_penalty"
                value = -abs(source_effect.value)
            else:
                kind = "healing_grace_aura_member"
                value = source_effect.value
            members.append(
                ActiveEffect(
                    id=f"{kind}:{source_effect.id}:{actor_id}",
                    actor_id=actor_id,
                    kind=kind,
                    label=source_effect.label,
                    object_id=source_effect.object_id,
                    value=value,
                    source_actor_id=str(active.source.id),
                    target_actor_id=actor_id,
                    source=source_effect.source,
                    duration=EffectDuration.CONCENTRATION,
                    stacking=EffectStackingPolicy.REPLACE,
                    stacking_key=f"spell-aura:{source_effect.id}:{actor_id}",
                    spell_level=source_effect.spell_level,
                    radius_feet=source_effect.radius_feet,
                    die_sides=source_effect.die_sides,
                    modifier=source_effect.modifier,
                    uses_maximum=source_effect.uses_maximum,
                    remaining_rounds=source_effect.remaining_rounds,
                )
            )
    return (*retained, *strongest_aura_members(members))


def resolve_healing_grace_bonus(
    actors: Sequence[Actor],
    active_effects: Sequence[ActiveEffect],
    target: Actor,
    *,
    rng: Random,
) -> HealingGraceResolution:
    """Spend one nearby Healing Grace activation and roll its bonus."""

    synchronized = synchronize_spell_aura_effects(actors, active_effects)
    candidate = max(
        (
            active
            for active in active_spell_auras(actors, synchronized)
            if active.effect.kind == "healing_grace_aura_source"
            and active.effect.value > 0
            and str(target.id) in active.affected_actor_ids
        ),
        key=lambda active: aura_effect_strength(active.effect),
        default=None,
    )
    if candidate is None:
        return HealingGraceResolution(synchronized)
    effect = candidate.effect
    die_sides = effect.die_sides or 8
    die_roll = rng.randint(1, die_sides)
    bonus = die_roll + effect.modifier
    remaining_uses = effect.value - 1
    updated = tuple(
        replace(item, value=remaining_uses)
        if item.id == effect.id and remaining_uses > 0
        else item
        for item in synchronized
        if item.id != effect.id or remaining_uses > 0
    )
    updated = synchronize_spell_aura_effects(actors, updated)
    return HealingGraceResolution(
        updated,
        bonus=bonus,
        die_roll=die_roll,
        source_actor_id=str(candidate.source.id),
        effect_id=effect.id,
    )


def _spell_aura_affects(
    source: Actor,
    target: Actor,
    effect: ActiveEffect,
) -> bool:
    if grid_distance_feet(source.position, target.position) > effect.radius_feet:
        return False
    same_faction = source.faction == target.faction
    if effect.kind == "divine_care_aura_source":
        return not same_faction and not target.is_defeated()
    return same_faction and not target.is_dead()


__all__ = [
    "ActiveAura",
    "ActiveSpellAura",
    "HealingGraceResolution",
    "SPELL_AURA_MEMBER_KINDS",
    "SPELL_AURA_SOURCE_KINDS",
    "active_auras",
    "active_spell_auras",
    "actor_is_affected_by_aura",
    "resolve_healing_grace_bonus",
    "saving_throw_aura_modifiers",
    "synchronize_spell_aura_effects",
]
