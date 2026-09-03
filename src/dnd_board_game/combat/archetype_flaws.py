"""Deterministic combat rules for the seven board-game archetype flaws."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from dnd_board_game.actors import Actor, Faction, actor_has_feature
from dnd_board_game.rules import (
    ActiveEffect,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    RollModifier,
    RollModifierType,
    RollMode,
)

from .conditions import ConditionState
from .spells import grid_distance_feet


FLAW_FEATURE_IDS: dict[str, tuple[str, str]] = {
    "garran": ("flaw_remorse", "Skaza: Wyrzuty sumienia"),
    "brakka": ("flaw_chains", "Skaza: Bitewny amok"),
    "mira": ("flaw_exposed_panic", "Skaza: Panika po zdemaskowaniu"),
    "dagna": ("flaw_leave_no_one", "Skaza: Nikogo nie zostawiam"),
    "lorian": ("flaw_needs_audience", "Skaza: Potrzeba publiczności"),
    "nimra": ("flaw_arcane_echo", "Skaza: Echo magicznego wycieku"),
    "erynd": ("flaw_friendly_fire_trauma", "Skaza: Trauma bratobójczego strzału"),
}

DYNAMIC_FLAW_KINDS = frozenset(
    {
        "flaw_command_guilt_active",
        "flaw_remorse_active",
        "flaw_chains_active",
        "flaw_triage_active",
        "flaw_friendly_fire_trauma_active",
    }
)


@dataclass(frozen=True, slots=True)
class FlawActivation:
    actor_id: str
    kind: str
    label: str
    value: int = 0
    target_actor_id: str | None = None

    def as_effect(self) -> ActiveEffect:
        return ActiveEffect(
            id=f"{self.kind}:{self.actor_id}",
            actor_id=self.actor_id,
            kind=self.kind,
            label=self.label,
            object_id=f"feature:{self.kind}",
            value=self.value,
            source=EffectSource(EffectSourceType.SYSTEM, self.kind, self.label),
            duration=EffectDuration.UNTIL_ENCOUNTER_END,
            target_actor_id=self.target_actor_id,
        )


def _living_downed_allies(actor: Actor, actors: Sequence[Actor]) -> tuple[Actor, ...]:
    return tuple(
        ally
        for ally in actors
        if ally.id != actor.id
        and ally.faction == actor.faction == Faction.ALLY
        and ally.hp <= 0
        and not ally.is_dead()
        and grid_distance_feet(actor.position, ally.position) <= 30
    )


def dynamic_flaw_activations(
    actors: Sequence[Actor],
    condition_states: Sequence[ConditionState] = (),
    damage_received_by_actor: Sequence[tuple[str, int]] = (),
) -> tuple[FlawActivation, ...]:
    """Derive live flaws from actor positions, HP and conditions."""
    activations: list[FlawActivation] = []
    for actor in actors:
        actor_id = str(actor.id)
        if actor.is_defeated():
            continue
        downed = _living_downed_allies(actor, actors)
        if actor_has_feature(actor, "flaw_remorse"):
            damage = dict(damage_received_by_actor)
            party = tuple(
                ally
                for ally in actors
                if ally.faction == actor.faction == Faction.ALLY
                and (ally.uses_death_saves or ally.id == actor.id)
            )
            own_damage = damage.get(actor_id, 0)
            ally_damage = tuple(
                damage.get(str(ally.id), 0)
                for ally in party
                if ally.id != actor.id
            )
            if ally_damage and any(value > own_damage for value in ally_damage) and all(
                value >= own_damage for value in ally_damage
            ):
                activations.append(
                    FlawActivation(
                        actor_id,
                        "flaw_remorse_active",
                        "Wyrzuty sumienia",
                        -2,
                    )
                )
        if actor_has_feature(actor, "flaw_leave_no_one") and downed:
            activations.append(
                FlawActivation(
                    actor_id,
                    "flaw_triage_active",
                    "Nikogo nie zostawiam",
                )
            )
        if actor_has_feature(actor, "flaw_friendly_fire_trauma"):
            adjacent_allies = sum(
                1
                for ally in actors
                if ally.id != actor.id
                and ally.faction == actor.faction == Faction.ALLY
                and ally.uses_death_saves
                and not ally.is_defeated()
                and ally.hp > 0
                and grid_distance_feet(actor.position, ally.position) <= 5
            )
            if adjacent_allies:
                activations.append(
                    FlawActivation(
                        actor_id,
                        "flaw_friendly_fire_trauma_active",
                        "Trauma bratobójczego strzału",
                        -adjacent_allies,
                    )
                )
    return tuple(activations)


def synchronize_dynamic_flaw_effects(
    actors: Sequence[Actor],
    condition_states: Sequence[ConditionState],
    active_effects: Sequence[ActiveEffect],
    damage_received_by_actor: Sequence[tuple[str, int]] = (),
) -> tuple[ActiveEffect, ...]:
    retained = tuple(
        effect for effect in active_effects if effect.kind not in DYNAMIC_FLAW_KINDS
    )
    return (
        *retained,
        *(
            item.as_effect()
            for item in dynamic_flaw_activations(
                actors,
                condition_states,
                damage_received_by_actor,
            )
        ),
    )


def _remorse_roll_modifiers(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> tuple[RollModifier, ...]:
    return tuple(
        RollModifier(
            effect.label,
            effect.value,
            RollModifierType.CUSTOM,
            stacking_key=effect.kind,
        )
        for effect in active_effects
        if effect.actor_id == str(actor.id) and effect.kind == "flaw_remorse_active"
    )


def flaw_attack_roll_modifiers(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
    source: object | None = None,
) -> tuple[RollModifier, ...]:
    modifiers = list(_remorse_roll_modifiers(actor, active_effects))
    bow_attack = source is None or (
        getattr(source, "source_item_id", None) == "longbow"
        and getattr(getattr(source, "attack_kind", None), "value", "") == "ranged"
    )
    if bow_attack:
        modifiers.extend(
            RollModifier(
                effect.label,
                effect.value,
                RollModifierType.CUSTOM,
                stacking_key=effect.kind,
            )
            for effect in active_effects
            if effect.actor_id == str(actor.id)
            and effect.kind == "flaw_friendly_fire_trauma_active"
        )
    return tuple(modifiers)


def attack_source_with_exposed_mira_bonus(
    hidden_states: Sequence[object],
    attacker: Actor,
    target: Actor,
    source: object,
) -> object:
    """Grant +2 to an observer who exposed Mira in this stealth session."""

    if (
        attacker.faction == target.faction
        or not actor_has_feature(target, "flaw_exposed_panic")
    ):
        return source
    hidden = next(
        (
            state
            for state in hidden_states
            if getattr(state, "actor_id", None) == str(target.id)
        ),
        None,
    )
    if hidden is None or str(attacker.id) in getattr(
        hidden, "hidden_from_actor_ids", ()
    ):
        return source
    request = getattr(source, "attack_roll_request", None)
    if request is None:
        return source
    return replace(
        source,
        attack_roll_request=replace(
            request,
            modifiers=(
                *request.modifiers,
                RollModifier(
                    "Panika Miry po zdemaskowaniu",
                    2,
                    RollModifierType.FEATURE,
                    stacking_key="flaw_exposed_panic_bonus",
                ),
            ),
        ),
    )


def flaw_ability_check_modifiers(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> tuple[RollModifier, ...]:
    return _remorse_roll_modifiers(actor, active_effects)


def flaw_saving_throw_modifiers(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> tuple[RollModifier, ...]:
    return _remorse_roll_modifiers(actor, active_effects)


def flaw_blocks_concentration_spell(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> bool:
    # Kept as a compatibility hook for restored snapshots.  Nimra's current
    # flaw blocks the previous round's spell/Metamagic, not Concentration.
    return False


def flaw_blocks_equipment_use(
    actor: Actor,
    active_effects: Sequence[ActiveEffect],
) -> bool:
    """Return whether Brakka's flaw blocks active item use during Rage.

    Held weapons remain usable: this rule blocks consumables, scrolls and item
    powers, not ordinary attacks made with already equipped weapons.
    """

    return actor_has_feature(actor, "flaw_chains") and any(
        effect.actor_id == str(actor.id) and effect.kind == "rage"
        for effect in active_effects
    )


__all__ = [
    "DYNAMIC_FLAW_KINDS",
    "FLAW_FEATURE_IDS",
    "FlawActivation",
    "dynamic_flaw_activations",
    "flaw_ability_check_modifiers",
    "flaw_attack_roll_modifiers",
    "attack_source_with_exposed_mira_bonus",
    "flaw_blocks_concentration_spell",
    "flaw_blocks_equipment_use",
    "flaw_saving_throw_modifiers",
    "synchronize_dynamic_flaw_effects",
]
