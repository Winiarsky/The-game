"""Deterministic rules for Erynd's mobile-hunter archetype."""

from __future__ import annotations

from dnd_board_game.actors.resources import uses_physical_mana

from dataclasses import dataclass, replace
from typing import Sequence

from dnd_board_game.actors import Actor, actor_has_feature
from dnd_board_game.rules import (
    ActiveEffect,
    AdditionalEffectExpiration,
    DiceExpression,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    EffectStackingPolicy,
    ability_modifier,
    apply_active_effect,
)

from .attack_flow import AttackKind, AttackSource, AttackSourceType
from .damage import DamageComponentSpec
from .session import CombatState, current_actor, use_movement_action, use_bonus_action


ERYND_ARROW_ACTION_IDS = frozenset(
    {"anchoring_arrow", "exposing_arrow", "disrupting_arrow", "double_shot"}
)


@dataclass(frozen=True, slots=True)
class EryndFeatureResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    action_id: str


def is_longbow_source(source: AttackSource) -> bool:
    return (
        source.source_type == AttackSourceType.WEAPON
        and source.attack_kind == AttackKind.RANGED
        and (source.source_item_id == "longbow" or source.proficiency_id == "longbow")
    )


def prepare_erynd_arrow(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    action_id: str,
    die_roll: int | None = None,
) -> EryndFeatureResolution:
    """Prepare one named bow attack without spending action/resource yet."""

    actor = current_actor(state)
    if action_id not in ERYND_ARROW_ACTION_IDS or not actor_has_feature(actor, action_id):
        raise ValueError("Aktywna postać nie posiada tej strzały Erynda.")
    if uses_physical_mana(actor):
        die_roll = 1 if action_id == "anchoring_arrow" else 2 if action_id == "exposing_arrow" else None
    die_sides = 4 if action_id == "anchoring_arrow" else 8 if action_id == "exposing_arrow" else 0
    if die_sides and (die_roll is None or not 1 <= die_roll <= die_sides):
        raise ValueError(f"{_arrow_label(action_id)} wymaga wyniku k{die_sides}.")
    if not die_sides and die_roll is not None:
        raise ValueError("Ta strzała nie wymaga dodatkowego rzutu.")
    effect = ActiveEffect(
        id=f"erynd_arrow_prepared:{actor.id}",
        actor_id=str(actor.id),
        kind="erynd_arrow_prepared",
        label=_arrow_label(action_id),
        object_id=f"class_feature:{action_id}",
        value=int(die_roll or 0),
        source_actor_id=str(actor.id),
        source=EffectSource(EffectSourceType.ACTION, action_id, _arrow_label(action_id)),
        duration=EffectDuration.UNTIL_TURN_END,
        expiration_actor_id=str(actor.id),
        additional_expirations=(
            AdditionalEffectExpiration(EffectDuration.UNTIL_TURN_END, actor_id=str(actor.id)),
        ),
        stacking=EffectStackingPolicy.REPLACE,
        stacking_key=f"erynd_arrow_prepared:{actor.id}",
    )
    return EryndFeatureResolution(
        state,
        apply_active_effect(active_effects, effect).active_effects,
        action_id,
    )


def prepared_erynd_arrow_source(
    actor: Actor,
    sources: Sequence[AttackSource],
    active_effects: Sequence[ActiveEffect],
) -> AttackSource | None:
    prep = next(
        (
            effect
            for effect in active_effects
            if effect.actor_id == str(actor.id) and effect.kind == "erynd_arrow_prepared"
        ),
        None,
    )
    if prep is None:
        return None
    action_id = prep.object_id.removeprefix("class_feature:")
    base = next((source for source in sources if is_longbow_source(source)), None)
    if base is None:
        return None
    components = base.damage_components
    if action_id == "double_shot" and components and not uses_physical_mana(actor):
        dexterity = ability_modifier(actor.ability_scores.dexterity)
        first = components[0]
        first = replace(
            first,
            dice=(DiceExpression(2, 8) if first.dice is not None else None),
            modifier=dexterity * 2,
            label="Podwójny strzał",
        )
        components = (first, *components[1:])
    rider = {
        "anchoring_arrow": (
            "Trafienie: cel wykonuje rzut Siły ST 14; porażka blokuje ruch, "
            "sukces zmniejsza ruch o połowę. Efekt trwa przez podany wynik k4 rund."
        ),
        "exposing_arrow": f"Trafienie: KP celu spada o {prep.value} do początku następnej tury Erynda.",
        "disrupting_arrow": (
            "Trafienie: cel traci reakcje, a jego następny atak ma utrudnienie; "
            "najpóźniej do końca jego następnej tury."
        ),
        "double_shot": (
            "Jeden test ataku i jeden cel. Znak łowcy "
            "i Pierwsza krew dodają kość tylko raz."
        ),
    }[action_id]
    return replace(
        base,
        id=action_id,
        name=_arrow_label(action_id),
        resource_pool_id="instinct",
        resource_cost=2 if action_id == "double_shot" else 1,
        ammunition_cost=1,
        damage_die_sides=(
            components[0].dice.sides
            if action_id == "double_shot" and components[0].dice is not None
            else base.damage_die_sides
        ),
        damage_modifier=(
            components[0].modifier
            if action_id == "double_shot"
            else base.damage_modifier
        ),
        damage_components=components,
        damage_hint=" + ".join(component.hint() for component in components),
        tabletop_riders=(*base.tabletop_riders, rider),
        on_hit_effect_kind=(
            "erynd_anchored"
            if action_id == "anchoring_arrow"
            else "erynd_exposed_ac"
            if action_id == "exposing_arrow"
            else "erynd_disrupted"
            if action_id == "disrupting_arrow"
            else None
        ),
        on_hit_effect_value=(prep.value if action_id in {"anchoring_arrow", "exposing_arrow"} else 1),
        on_hit_effect_duration=(
            # remaining_rounds owns the k4 countdown; encounter duration only
            # guarantees cleanup if combat ends before that countdown.
            EffectDuration.UNTIL_ENCOUNTER_END
            if action_id == "anchoring_arrow"
            else EffectDuration.UNTIL_NEXT_ATTACK
            if action_id == "disrupting_arrow"
            else EffectDuration.UNTIL_TURN_START
        ),
        on_hit_effect_remaining_rounds=(prep.value if action_id == "anchoring_arrow" else None),
        on_hit_save_ability=("strength" if action_id == "anchoring_arrow" else None),
        on_hit_save_dc=(8 + actor.proficiency_bonus + ability_modifier(actor.ability_scores.dexterity) if action_id == "anchoring_arrow" else 0),
        on_hit_save_success_effect_kind=("erynd_anchor_half_movement" if action_id == "anchoring_arrow" else None),
    )


def erynd_arrow_attack_sources(
    actor: Actor,
    sources: Sequence[AttackSource],
) -> tuple[AttackSource, ...]:
    """Build stable source variants, including every physical die result."""

    base = next((source for source in sources if is_longbow_source(source)), None)
    if base is None:
        return ()
    variants: list[AttackSource] = []
    for action_id, rolls in (
        ("anchoring_arrow", range(1, 5)),
        ("exposing_arrow", range(1, 9)),
        ("disrupting_arrow", (0,)),
        ("double_shot", (0,)),
    ):
        if not actor_has_feature(actor, action_id):
            continue
        for die_roll in rolls:
            prep = ActiveEffect(
                id=f"erynd_arrow_variant:{actor.id}:{action_id}:{die_roll}",
                actor_id=str(actor.id),
                kind="erynd_arrow_prepared",
                label=_arrow_label(action_id),
                object_id=f"class_feature:{action_id}",
                value=die_roll,
                source_actor_id=str(actor.id),
                duration=EffectDuration.UNTIL_TURN_END,
            )
            variant = prepared_erynd_arrow_source(actor, (base,), (prep,))
            assert variant is not None
            variants.append(
                replace(
                    variant,
                    id=(f"{action_id}:{die_roll}" if die_roll else action_id),
                )
            )
    return tuple(variants)


def erynd_arrow_action_id(source_id: str) -> str | None:
    action_id = source_id.partition(":")[0]
    return action_id if action_id in ERYND_ARROW_ACTION_IDS else None


def resolve_erynd_aim(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> EryndFeatureResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "aim"):
        raise ValueError("Aktywna postać nie posiada Celowania.")
    if uses_physical_mana(actor):
        bonus = use_bonus_action(state)
        if not bonus.accepted:
            raise ValueError(bonus.message)
        state = bonus.state
    movement = use_movement_action(state, actor)
    if not movement.accepted:
        raise ValueError(movement.message)
    effect = ActiveEffect(
        id=f"erynd_aim:{actor.id}",
        actor_id=str(actor.id),
        kind="erynd_aim_advantage",
        label="Celowanie",
        object_id="class_feature:aim",
        value=0,
        source_actor_id=str(actor.id),
        source=EffectSource(EffectSourceType.ACTION, "aim", "Celowanie"),
        duration=EffectDuration.UNTIL_NEXT_ATTACK,
        expiration_actor_id=str(actor.id),
        additional_expirations=(
            AdditionalEffectExpiration(EffectDuration.UNTIL_TURN_END, actor_id=str(actor.id)),
        ),
    )
    return EryndFeatureResolution(
        movement.state,
        apply_active_effect(active_effects, effect).active_effects,
        "aim",
    )


def first_blood_damage(actor: Actor, target: Actor, damage_type) -> DamageComponentSpec | None:
    if not actor_has_feature(actor, "first_blood") or target.hp != target.max_hp or target.hp <= 0:
        return None
    return DamageComponentSpec(
        id="first_blood",
        damage_type=damage_type,
        dice=DiceExpression(1, 6 if uses_physical_mana(actor) else 8),
        label="Pierwsza krew",
    )


def commit_first_blood_hit(
    active_effects: tuple[ActiveEffect, ...],
    actor_id: str,
) -> tuple[ActiveEffect, ...]:
    marker = ActiveEffect(
        id=f"first_blood_used:{actor_id}",
        actor_id=actor_id,
        kind="first_blood_used",
        label="Pierwsza krew wykorzystana",
        object_id="class_feature:first_blood",
        value=1,
        source_actor_id=actor_id,
        duration=EffectDuration.UNTIL_TURN_START,
        expiration_actor_id=actor_id,
    )
    return apply_active_effect(active_effects, marker).active_effects


def _arrow_label(action_id: str) -> str:
    return {
        "anchoring_arrow": "Strzała kotwicząca",
        "exposing_arrow": "Strzała odsłaniająca",
        "disrupting_arrow": "Strzała zakłócająca",
        "double_shot": "Podwójny strzał",
    }[action_id]


__all__ = [
    "ERYND_ARROW_ACTION_IDS",
    "EryndFeatureResolution",
    "first_blood_damage",
    "commit_first_blood_hit",
    "erynd_arrow_action_id",
    "erynd_arrow_attack_sources",
    "is_longbow_source",
    "prepare_erynd_arrow",
    "prepared_erynd_arrow_source",
    "resolve_erynd_aim",
]
