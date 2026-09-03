"""Deterministic rules for Lorian's crossbow-controller archetype."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Sequence

from dnd_board_game.actors import Actor, actor_has_feature
from dnd_board_game.rules import (
    ActiveEffect,
    D20RollRequest,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    EffectStackingPolicy,
    RollModifier,
    RollModifierType,
    ability_modifier,
    apply_active_effect,
)

from .attack_flow import AttackKind, AttackSource, AttackSourceType
from .conditions import CombatCondition, ConditionState
from .spells import (
    SpellArea,
    SpellAreaShape,
    SpellAreaTargetMode,
    SpellSaveResult,
    grid_distance_feet,
)
from .session import CombatState, current_actor


LORIAN_SINGLE_SHOT_ACTION_IDS = frozenset({"mocking_shot", "provoking_shot"})
LORIAN_SHOT_ACTION_IDS = frozenset(
    {*LORIAN_SINGLE_SHOT_ACTION_IDS, "optical_scope", "entangling_shot"}
)
LORIAN_AUDIENCE_ACTION_IDS = frozenset(
    {
        "bardic_inspiration",
        "optical_scope",
        "mocking_shot",
        "provoking_shot",
        "entangling_shot",
        "counterpoint",
        "distracting_shout",
        "cutting_words",
    }
)


@dataclass(frozen=True, slots=True)
class LorianFeatureResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    action_id: str


def is_lorian_hand_crossbow_source(source: AttackSource) -> bool:
    return (
        source.source_type == AttackSourceType.WEAPON
        and source.attack_kind == AttackKind.RANGED
        and (
            source.source_item_id == "hand_crossbow"
            or source.proficiency_id == "hand_crossbow"
        )
    )


def lorian_hand_crossbow_source(source: AttackSource) -> AttackSource:
    """Apply the board-game crossbow contract without ammunition bookkeeping."""

    if not is_lorian_hand_crossbow_source(source):
        return source
    return replace(
        source,
        range_feet=45,
        long_range_feet=None,
        ammunition_type=None,
        ammunition_cost=1,
        loading=False,
    )


def lorian_attacks_per_action(actor: Actor, source: AttackSource) -> int:
    """Kusznik grants exactly two attacks, but only with Lorian's hand crossbow."""

    if (
        str(actor.id) == "lorian"
        and actor_has_feature(actor, "crossbowman")
        and is_lorian_hand_crossbow_source(source)
        and source.id not in LORIAN_SINGLE_SHOT_ACTION_IDS
    ):
        return 2
    return actor.attacks_per_action


def prepare_lorian_shot(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    action_id: str,
) -> LorianFeatureResolution:
    """Prepare a special shot; the attack action is spent only on resolution."""

    actor = current_actor(state)
    if (
        action_id not in LORIAN_SHOT_ACTION_IDS
        or not actor_has_feature(actor, action_id)
    ):
        raise ValueError("Aktywna postać nie posiada tej techniki Loriena.")
    require_lorian_audience(
        actor,
        state.actors,
        action_id,
        condition_states=state.condition_states,
    )
    if action_id == "optical_scope" and (
        state.turn_action.movement_action_used
        or state.turn_action.movement_used_feet > 0
    ):
        raise ValueError("Lunetę optyczną trzeba wybrać przed ruchem Loriena.")
    effect = ActiveEffect(
        id=f"lorian_shot_prepared:{actor.id}",
        actor_id=str(actor.id),
        kind="lorian_shot_prepared",
        label=lorian_shot_label(action_id),
        object_id=f"class_feature:{action_id}",
        value=0,
        source_actor_id=str(actor.id),
        source=EffectSource(
            EffectSourceType.ACTION,
            action_id,
            lorian_shot_label(action_id),
        ),
        duration=EffectDuration.UNTIL_TURN_END,
        expiration_actor_id=str(actor.id),
        stacking=EffectStackingPolicy.REPLACE,
        stacking_key=f"lorian_shot_prepared:{actor.id}",
    )
    return LorianFeatureResolution(
        state,
        apply_active_effect(active_effects, effect).active_effects,
        action_id,
    )


def prepared_lorian_shot_source(
    actor: Actor,
    sources: Sequence[AttackSource],
    active_effects: Sequence[ActiveEffect],
) -> AttackSource | None:
    prepared = next(
        (
            effect
            for effect in active_effects
            if effect.actor_id == str(actor.id)
            and effect.kind == "lorian_shot_prepared"
        ),
        None,
    )
    if prepared is None:
        return None
    action_id = prepared.object_id.removeprefix("class_feature:")
    if action_id not in LORIAN_SHOT_ACTION_IDS:
        return None
    base = next(
        (
            lorian_hand_crossbow_source(source)
            for source in sources
            if is_lorian_hand_crossbow_source(source)
        ),
        None,
    )
    if base is None:
        return None
    if action_id == "entangling_shot":
        return lorian_entangling_shot_source(actor, (base,))
    request = base.attack_roll_request
    if action_id == "optical_scope":
        request = replace(
            request,
            modifiers=(
                *request.modifiers,
                RollModifier(
                    "Luneta optyczna: −2 KP celu",
                    2,
                    RollModifierType.FEATURE,
                    stacking_key="lorian_optical_scope",
                ),
            ),
        )
    return replace(
        base,
        id=action_id,
        name=lorian_shot_label(action_id),
        range_feet=60 if action_id == "optical_scope" else base.range_feet,
        attack_roll_request=request,
        limited_attacks=action_id in LORIAN_SINGLE_SHOT_ACTION_IDS,
        on_hit_effect_kind=(
            "lorian_mocked_attack"
            if action_id == "mocking_shot"
            else "lorian_provoked" if action_id == "provoking_shot" else None
        ),
        on_hit_effect_duration=(
            EffectDuration.UNTIL_NEXT_ATTACK
            if action_id == "mocking_shot"
            else EffectDuration.UNTIL_TURN_START
        ),
        tabletop_riders=(*base.tabletop_riders, _shot_rider(action_id)),
    )


def lorian_entangling_shot_source(
    actor: Actor,
    sources: Sequence[AttackSource],
) -> AttackSource | None:
    """Build the friendly-fire 3x3 control shot from Lorian's crossbow."""

    if str(actor.id) != "lorian" or not actor_has_feature(actor, "entangling_shot"):
        return None
    base = next(
        (
            lorian_hand_crossbow_source(source)
            for source in sources
            if is_lorian_hand_crossbow_source(source)
        ),
        None,
    )
    if base is None:
        return None
    return replace(
        base,
        id="entangling_shot",
        name="Oplatający ostrzał",
        source_type=AttackSourceType.CUSTOM,
        range_feet=45,
        area=SpellArea(
            SpellAreaShape.CUBE,
            length_feet=15,
            width_feet=15,
            target_mode=SpellAreaTargetMode.ALL_CREATURES,
        ),
        save_ability="dexterity",
        save_dc=max(
            1,
            actor.spell_save_dc
            or 8 + actor.proficiency_bonus + ability_modifier(actor.ability_scores.charisma),
        ),
        damage_hint="0",
        damage_fixed=0,
        damage_die_sides=None,
        damage_modifier=0,
        damage_components=(),
        source_item_id=None,
        ammunition_type=None,
        loading=False,
        limited_attacks=True,
        tabletop_riders=(
            "Obszar 3×3. Sukces obrony: połowa ruchu; porażka: brak ruchu "
            "do początku następnej tury Loriena. Działa również na sojuszników.",
        ),
    )


def lorian_attack_sources(
    actor: Actor,
    sources: Sequence[AttackSource],
) -> tuple[AttackSource, ...]:
    """Normalize ordinary hand-crossbow sources shown to Lorian."""

    return tuple(
        lorian_hand_crossbow_source(source)
        if str(actor.id) == "lorian"
        else source
        for source in sources
    )


def lorian_shot_action_id(source_id: str) -> str | None:
    action_id = source_id.partition(":")[0]
    return action_id if action_id in LORIAN_SHOT_ACTION_IDS else None


def apply_lorian_shot_companion_effects(
    active_effects: tuple[ActiveEffect, ...],
    *,
    attacker_id: str,
    target_id: str,
    source: AttackSource,
) -> tuple[ActiveEffect, ...]:
    """Add status parts which cannot share the primary on-hit expiration."""

    if source.on_hit_effect_kind != "lorian_mocked_attack":
        return active_effects
    effect = ActiveEffect(
        id=f"lorian_mocked_wisdom:{attacker_id}:{target_id}",
        actor_id=target_id,
        kind="lorian_mocked_wisdom",
        label="Ostrzał destabilizujący: zachwiana wola",
        object_id="class_feature:mocking_shot",
        value=1,
        source_actor_id=attacker_id,
        target_actor_id=target_id,
        source=EffectSource(
            EffectSourceType.ACTION,
            "mocking_shot",
            "Ostrzał destabilizujący",
        ),
        duration=EffectDuration.UNTIL_TURN_START,
        expiration_actor_id=attacker_id,
        stacking=EffectStackingPolicy.REFRESH,
        stacking_key=f"lorian_mocked_wisdom:{target_id}",
    )
    return apply_active_effect(active_effects, effect).active_effects


def lorian_shot_label(action_id: str) -> str:
    return {
        "mocking_shot": "Ostrzał destabilizujący",
        "provoking_shot": "Prowokujący ostrzał",
        "optical_scope": "Luneta optyczna",
        "entangling_shot": "Oplatający ostrzał",
    }[action_id]


def lorian_has_live_audience(
    actor: Actor,
    actors: Sequence[Actor],
    *,
    maximum_distance_feet: int = 10,
    condition_states: Sequence[ConditionState] = (),
) -> bool:
    """Return whether Lorian's inventor tricks have a conscious ally nearby."""

    if not actor_has_feature(actor, "flaw_needs_audience"):
        return True
    return any(
        candidate.id != actor.id
        and candidate.faction == actor.faction
        and not candidate.is_defeated()
        and candidate.hp > 0
        and not any(
            condition.actor_id == str(candidate.id)
            and condition.condition
            in {CombatCondition.UNCONSCIOUS, CombatCondition.INCAPACITATED}
            for condition in condition_states
        )
        and grid_distance_feet(actor.position, candidate.position)
        <= maximum_distance_feet
        for candidate in actors
    )


def require_lorian_audience(
    actor: Actor,
    actors: Sequence[Actor],
    action_id: str,
    *,
    condition_states: Sequence[ConditionState] = (),
) -> None:
    if (
        action_id in LORIAN_AUDIENCE_ACTION_IDS
        and not lorian_has_live_audience(
            actor,
            actors,
            condition_states=condition_states,
        )
    ):
        raise ValueError(
            "Lorian potrzebuje żywego i przytomnego sojusznika w odległości "
            "10 stóp, aby użyć tej zdolności specjalnej."
        )


def validate_lorian_optical_target(
    active_effects: Sequence[ActiveEffect],
    *,
    attacker_id: str,
    target_id: str,
    source: AttackSource,
) -> None:
    if source.id != "optical_scope":
        return
    locked = next(
        (
            effect.target_actor_id
            for effect in active_effects
            if effect.actor_id == attacker_id
            and effect.kind == "lorian_optical_target_lock"
        ),
        None,
    )
    if locked is not None and locked != target_id:
        raise ValueError("Oba strzały z Lunety optycznej muszą trafić w ten sam cel.")


def apply_lorian_optical_target_lock(
    active_effects: tuple[ActiveEffect, ...],
    *,
    attacker_id: str,
    target_id: str,
    source: AttackSource,
) -> tuple[ActiveEffect, ...]:
    if source.id != "optical_scope":
        return active_effects
    effect = ActiveEffect(
        id=f"lorian_optical_target_lock:{attacker_id}",
        actor_id=attacker_id,
        kind="lorian_optical_target_lock",
        label="Luneta optyczna: namierzony cel",
        object_id="class_feature:optical_scope",
        value=0,
        source_actor_id=attacker_id,
        target_actor_id=target_id,
        source=EffectSource(EffectSourceType.ACTION, "optical_scope", "Luneta optyczna"),
        duration=EffectDuration.UNTIL_TURN_END,
        expiration_actor_id=attacker_id,
        stacking=EffectStackingPolicy.REPLACE,
        stacking_key=f"lorian_optical_target_lock:{attacker_id}",
    )
    return apply_active_effect(active_effects, effect).active_effects


def apply_lorian_entangling_effects(
    active_effects: tuple[ActiveEffect, ...],
    *,
    attacker_id: str,
    saving_throws: Sequence[SpellSaveResult],
) -> tuple[ActiveEffect, ...]:
    """Apply the movement result of Oplatający ostrzał to every saved target."""

    updated = active_effects
    for saving_throw in saving_throws:
        kind = (
            "lorian_entangled_half_movement"
            if saving_throw.success
            else "lorian_entangled_no_movement"
        )
        label = (
            "Oplatający ostrzał: połowa ruchu"
            if saving_throw.success
            else "Oplatający ostrzał: brak ruchu"
        )
        effect = ActiveEffect(
            id=f"{kind}:{attacker_id}:{saving_throw.actor_id}",
            actor_id=saving_throw.actor_id,
            kind=kind,
            label=label,
            object_id="class_feature:entangling_shot",
            value=0,
            source_actor_id=attacker_id,
            target_actor_id=saving_throw.actor_id,
            source=EffectSource(
                EffectSourceType.ACTION,
                "entangling_shot",
                "Oplatający ostrzał",
            ),
            duration=EffectDuration.UNTIL_TURN_START,
            expiration_actor_id=attacker_id,
            stacking=EffectStackingPolicy.REFRESH,
            stacking_key=f"lorian_entangled:{saving_throw.actor_id}",
        )
        updated = apply_active_effect(updated, effect).active_effects
    return updated


def update_lorian_provocation_value(
    active_effects: tuple[ActiveEffect, ...],
    *,
    attacker_id: str,
    target_id: str,
    damage_dealt: int,
) -> tuple[ActiveEffect, ...]:
    """Store the actual wound as the provocation's attack modifier."""

    return tuple(
        replace(effect, value=max(0, int(damage_dealt)))
        if effect.kind == "lorian_provoked"
        and effect.source_actor_id == attacker_id
        and effect.actor_id == target_id
        else effect
        for effect in active_effects
    )


def social_grace_bonus(
    actor: Actor,
    *,
    ability: str,
    skill: str | None,
    in_combat: bool,
    verbal: bool = True,
) -> int:
    """Return Lorian's broad non-combat Charisma bonus."""

    if (
        in_combat
        or str(actor.id) != "lorian"
        or not actor_has_feature(actor, "social_grace_bargaining")
        or ability != "charisma"
    ):
        return 0
    return 2


def _shot_rider(action_id: str) -> str:
    if action_id == "mocking_shot":
        return (
            "Zastępuje oba zwykłe strzały. Trafienie daje utrudnienie do "
            "pierwszego ataku celu oraz do obron na Mądrość do początku "
            "następnej tury Loriena."
        )
    return (
        "Zastępuje oba zwykłe strzały. Do początku następnej tury Loriena "
        "premia do ataków przeciw niemu i kara przeciw pozostałym celom są "
        "równe faktycznie zadanym obrażeniom."
    )


__all__ = [
    "LORIAN_SHOT_ACTION_IDS",
    "LORIAN_SINGLE_SHOT_ACTION_IDS",
    "LORIAN_AUDIENCE_ACTION_IDS",
    "LorianFeatureResolution",
    "apply_lorian_entangling_effects",
    "apply_lorian_optical_target_lock",
    "apply_lorian_shot_companion_effects",
    "is_lorian_hand_crossbow_source",
    "lorian_attack_sources",
    "lorian_attacks_per_action",
    "lorian_entangling_shot_source",
    "lorian_hand_crossbow_source",
    "lorian_has_live_audience",
    "lorian_shot_action_id",
    "lorian_shot_label",
    "prepare_lorian_shot",
    "prepared_lorian_shot_source",
    "require_lorian_audience",
    "social_grace_bonus",
    "update_lorian_provocation_value",
    "validate_lorian_optical_target",
]
