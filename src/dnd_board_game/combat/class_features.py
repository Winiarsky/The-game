"""Executable level-1 class features shared by custom and authored actors."""

from __future__ import annotations

from dataclasses import dataclass, replace

from dnd_board_game.actors import (
    Actor,
    actor_resource_pool,
    actor_has_feature,
    can_spend_actor_resource,
    increase_exhaustion,
    spend_actor_resource,
)
from dnd_board_game.inventory import WeaponProperty, normalize_hand_equipment
from dnd_board_game.actors import skill_modifier
from dnd_board_game.rules import (
    ActiveEffect,
    AdditionalEffectExpiration,
    D20RollRequest,
    DiceExpression,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    RollMode,
    SavingThrowRequest,
    SavingThrowResult,
    ability_modifier,
    apply_active_effect,
)

from .action_economy import ActionEconomyCost, ActionUse
from .attack_flow import AttackKind, AttackSource, AttackSourceType
from .conditions import CombatCondition, apply_condition
from .damage import DamageComponentSpec, DamageType
from .healing import AppliedHealingResult, HealingSource, HealingSourceType, apply_healing_result
from .session import (
    CombatState,
    current_actor,
    grant_bonus_attacks,
    replace_actor,
    use_action_economy_cost,
)
from .spells import consume_spell_resource, grid_distance_feet
from .spells import SpellArea, SpellAreaShape, SpellAreaTargetMode
from .spells import resolve_actor_saving_throw
from .class_feature_rules import (
    FontOfMagicConversion,
    PreserveLifeAllocation,
    available_wild_shape_forms,
    bardic_inspiration_die_sides,
    convert_spell_slot_to_sorcery_points,
    create_spell_slot_from_sorcery_points,
    open_hand_technique_save_dc,
    revert_wild_shape,
    transform_into_wild_shape,
    validate_preserve_life_allocations,
)
from dnd_board_game.world import BoardState, Coordinate, line_of_sight_clear


@dataclass(frozen=True, slots=True)
class SecondWindResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    healing: AppliedHealingResult
    natural_roll: int


@dataclass(frozen=True, slots=True)
class ActionSurgeResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor


@dataclass(frozen=True, slots=True)
class OpenHandTechniqueResolution:
    state: CombatState
    attacker: Actor
    target_before: Actor
    target_after: Actor
    mode: str
    saving_throw: SavingThrowResult | None
    succeeded: bool
    push_destination: Coordinate | None = None


@dataclass(frozen=True, slots=True)
class RageResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    actor_before: Actor
    actor_after: Actor
    activated: bool
    exhaustion_added: bool = False


@dataclass(frozen=True, slots=True)
class LayOnHandsResolution:
    state: CombatState
    healer_before: Actor
    healer_after: Actor
    target_before: Actor
    target_after: Actor
    healing: AppliedHealingResult
    points_spent: int


@dataclass(frozen=True, slots=True)
class RecklessAttackResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    actor: Actor


@dataclass(frozen=True, slots=True)
class BrakkaFeatureResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    actor_before: Actor
    actor_after: Actor
    feature_id: str
    ferocity_spent: int = 0


@dataclass(frozen=True, slots=True)
class HardAsRockResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    incoming_damage: int
    reduction: int
    remaining_damage: int
    die_roll: int


@dataclass(frozen=True, slots=True)
class ShoulderCheckResolution:
    state: CombatState
    attacker: Actor
    target_before: Actor
    target_after: Actor
    attacker_total: int
    defender_total: int
    push_distance_feet: int
    succeeded: bool


@dataclass(frozen=True, slots=True)
class BardicInspirationResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    bard_before: Actor
    bard_after: Actor
    target: Actor
    die_sides: int


@dataclass(frozen=True, slots=True)
class PreserveLifeResolution:
    state: CombatState
    cleric_before: Actor
    cleric_after: Actor
    healed_actor_ids: tuple[str, ...]
    healing_spent: int


@dataclass(frozen=True, slots=True)
class KiDefenseResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    actor_before: Actor
    actor_after: Actor
    feature_id: str


@dataclass(frozen=True, slots=True)
class LimitedDodgeResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    actor_before: Actor
    actor_after: Actor
    feature_id: str


@dataclass(frozen=True, slots=True)
class FontOfMagicResolution:
    state: CombatState
    conversion: FontOfMagicConversion


@dataclass(frozen=True, slots=True)
class DivineSenseResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    detected_creature_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SacredWeaponResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    actor_before: Actor
    actor_after: Actor
    weapon_item_id: str
    attack_bonus: int


@dataclass(frozen=True, slots=True)
class BonusStrikeResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    attacks_granted: int
    source_id: str
    ki_spent: int


@dataclass(frozen=True, slots=True)
class WildShapeResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    form_id: str
    reverted: bool


@dataclass(frozen=True, slots=True)
class ChannelTurnResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    eligible_target_ids: tuple[str, ...]
    turned_target_ids: tuple[str, ...]
    successful_save_target_ids: tuple[str, ...]
    action_id: str


@dataclass(frozen=True, slots=True)
class PrimevalAwarenessResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    slot_level: int
    duration_minutes: int
    detected_creature_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FrenzyResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    actor: Actor
    activated: bool
    bonus_attack_source_id: str | None


@dataclass(frozen=True, slots=True)
class PactWeaponResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    weapon_form_id: str


def resolve_pact_weapon(
    state: CombatState,
    weapon: object,
) -> PactWeaponResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "pact_of_the_blade"):
        raise ValueError("Aktywna postać nie posiada Pact of the Blade.")
    if getattr(weapon, "kind", "") != "weapon":
        raise ValueError("Pact Weapon musi mieć formę broni.")
    if getattr(weapon, "ammunition_type", None) is not None:
        raise ValueError("Pact Weapon musi być bronią do walki wręcz.")
    action = use_action_economy_cost(state, ActionEconomyCost.ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    actor_after_action = current_actor(action.state)
    source_ref = str(getattr(weapon, "source_ref", None) or getattr(weapon, "id"))
    pact_weapon = replace(
        weapon,
        id="pact_weapon",
        name=f"Pact Weapon: {getattr(weapon, 'name')}",
        source_ref=source_ref,
        quantity=1,
        equipped=True,
    )
    inventory = tuple(
        item
        for item in actor_after_action.inventory
        if item.id != "pact_weapon"
    )
    actor_after = replace(
        actor_after_action,
        inventory=normalize_hand_equipment((*inventory, pact_weapon)),
    )
    return PactWeaponResolution(
        replace_actor(action.state, actor_after),
        actor,
        actor_after,
        source_ref,
    )


def resolve_frenzy(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> FrenzyResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "frenzy"):
        raise ValueError("Aktywna postać nie posiada Frenzy.")
    rage = next(
        (
            effect
            for effect in active_effects
            if effect.actor_id == str(actor.id) and effect.kind == "rage"
        ),
        None,
    )
    if rage is None:
        raise ValueError("Frenzy można aktywować tylko podczas Rage.")
    frenzy = next(
        (
            effect
            for effect in active_effects
            if effect.actor_id == str(actor.id) and effect.kind == "frenzy"
        ),
        None,
    )
    if frenzy is None:
        effect = ActiveEffect(
            id=f"frenzy:{actor.id}",
            actor_id=str(actor.id),
            kind="frenzy",
            label="Frenzy",
            object_id="class_feature:frenzy",
            value=1,
            source_actor_id=str(actor.id),
            source=EffectSource(
                EffectSourceType.ACTION,
                "frenzy",
                "Frenzy",
            ),
            duration=EffectDuration.UNTIL_ENCOUNTER_END,
        )
        effects = apply_active_effect(active_effects, effect).active_effects
        pending = ActiveEffect(
            id=f"frenzy_pending:{actor.id}",
            actor_id=str(actor.id),
            kind="frenzy_pending",
            label="Szał bojowy — oczekiwanie",
            object_id="class_feature:frenzy",
            value=0,
            source_actor_id=str(actor.id),
            source=EffectSource(
                EffectSourceType.ACTION,
                "frenzy",
                "Szał bojowy",
            ),
            duration=EffectDuration.UNTIL_TURN_END,
            expiration_actor_id=str(actor.id),
        )
        effects = apply_active_effect(effects, pending).active_effects
        return FrenzyResolution(state, effects, actor, True, None)
    if any(
        effect.actor_id == str(actor.id) and effect.kind == "frenzy_pending"
        for effect in active_effects
    ):
        raise ValueError("Dodatkowy atak Szału bojowego jest dostępny od następnej tury.")
    weapons = tuple(
        item
        for item in normalize_hand_equipment(actor.inventory)
        if item.kind == "weapon"
        and item.equipped
        and item.available
        and not item.broken
    )
    if not weapons:
        raise ValueError("Frenzy wymaga trzymanej broni do walki wręcz.")
    weapon = weapons[0]
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    source_id = weapon.source_ref or weapon.id
    updated = grant_bonus_attacks(
        action.state,
        count=1,
        source_id=source_id,
    )
    return FrenzyResolution(updated, active_effects, actor, False, source_id)


def resolve_primeval_awareness(
    state: CombatState,
    *,
    slot_level: int,
) -> PrimevalAwarenessResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "primeval_awareness"):
        raise ValueError("Aktywna postać nie posiada Primeval Awareness.")
    if slot_level < 1:
        raise ValueError("Primeval Awareness wymaga slotu co najmniej 1. poziomu.")
    action = use_action_economy_cost(state, ActionEconomyCost.ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    use = consume_spell_resource(
        current_actor(action.state),
        slot_level,
        cast_level=slot_level,
    )
    updated = replace_actor(action.state, use.actor_after)
    relevant_types = {
        "aberration",
        "celestial",
        "dragon",
        "elemental",
        "fey",
        "fiend",
        "undead",
    }
    detected = tuple(
        sorted(
            {
                target.creature_type
                for target in updated.actors
                if target.id != actor.id
                and not target.is_defeated()
                and target.creature_type in relevant_types
            }
        )
    )
    return PrimevalAwarenessResolution(
        updated,
        actor,
        use.actor_after,
        slot_level,
        slot_level,
        detected,
    )


def channel_turn_targets(
    state: CombatState,
    *,
    action_id: str,
    board: BoardState | None = None,
    actor: Actor | None = None,
) -> tuple[Actor, ...]:
    source = actor or current_actor(state)
    target_types = (
        {"undead"}
        if action_id == "turn_undead"
        else {"fiend", "undead"}
        if action_id == "turn_the_unholy"
        else set()
    )
    if not target_types:
        return ()
    return tuple(
        target
        for target in state.actors
        if target.id != source.id
        and not target.is_defeated()
        and target.creature_type in target_types
        and grid_distance_feet(source.position, target.position) <= 30
        and (
            board is None
            or line_of_sight_clear(board, source.position, target.position)
        )
    )


def resolve_channel_turn(
    state: CombatState,
    *,
    action_id: str,
    saving_rolls: dict[str, int],
    board: BoardState | None = None,
) -> ChannelTurnResolution:
    actor = current_actor(state)
    target_types = (
        {"undead"}
        if action_id == "turn_undead"
        else {"fiend", "undead"}
        if action_id == "turn_the_unholy"
        else set()
    )
    required_feature = (
        "channel_divinity_turn_the_unholy"
        if action_id == "turn_the_unholy"
        else action_id
    )
    if not target_types or not actor_has_feature(actor, required_feature):
        raise ValueError("Aktywna postać nie posiada wybranego odpędzania.")
    if not can_spend_actor_resource(actor, "channel_divinity_uses"):
        raise ValueError("Brak użyć Channel Divinity.")
    eligible = channel_turn_targets(
        state,
        action_id=action_id,
        board=board,
        actor=actor,
    )
    eligible_ids = tuple(str(target.id) for target in eligible)
    if set(saving_rolls) != set(eligible_ids):
        raise ValueError(
            "Podaj wynik rzutu obronnego Wisdom dla każdego celu odpędzania."
        )
    action = use_action_economy_cost(state, ActionEconomyCost.ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(
        current_actor(action.state),
        "channel_divinity_uses",
    )
    updated = replace_actor(action.state, spent.actor_after)
    conditions = updated.condition_states
    turned: list[str] = []
    successful: list[str] = []
    dc = actor.spell_save_dc
    if dc < 1:
        raise ValueError("Postać nie ma poprawnego ST Channel Divinity.")
    request = SavingThrowRequest(
        ability="wisdom",
        dc=dc,
        source_label="Channel Divinity",
        dc_source_label="ST Channel Divinity",
    )
    for target in eligible:
        target_id = str(target.id)
        save = resolve_actor_saving_throw(
            target,
            request,
            natural_roll=int(saving_rolls[target_id]),
            condition_states=conditions,
            combat_actors=updated.actors,
        )
        if save.success:
            successful.append(target_id)
            continue
        applied = apply_condition(
            conditions,
            target,
            CombatCondition.TURNED,
            source_actor_id=str(actor.id),
            source_label=(
                "Turn Undead"
                if action_id == "turn_undead"
                else "Turn the Unholy"
            ),
            duration=EffectDuration.UNTIL_ENCOUNTER_END,
            expiration_actor_id=str(actor.id),
        )
        conditions = applied.condition_states
        if applied.applied:
            turned.append(target_id)
    return ChannelTurnResolution(
        replace(updated, condition_states=conditions),
        actor,
        spent.actor_after,
        eligible_ids,
        tuple(turned),
        tuple(successful),
        action_id,
    )


def resolve_wild_shape(
    state: CombatState,
    *,
    form_id: str = "",
) -> WildShapeResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "wild_shape"):
        raise ValueError("Aktywna postać nie posiada Wild Shape.")
    if actor.wild_shape is not None:
        action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
        if not action.accepted:
            raise ValueError(action.message)
        actor_after = revert_wild_shape(current_actor(action.state))
        return WildShapeResolution(
            replace_actor(action.state, actor_after),
            actor,
            actor_after,
            actor.wild_shape.form_id,
            True,
        )
    if not form_id:
        raise ValueError("Wybierz formę Wild Shape.")
    if not can_spend_actor_resource(actor, "wild_shape_uses"):
        raise ValueError("Brak użyć Wild Shape.")
    legal_ids = {form.id for form in available_wild_shape_forms(actor)}
    if form_id not in legal_ids:
        raise ValueError("Wybrana forma Wild Shape nie jest dostępna.")
    action = use_action_economy_cost(state, ActionEconomyCost.ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(current_actor(action.state), "wild_shape_uses")
    actor_after = transform_into_wild_shape(spent.actor_after, form_id)
    return WildShapeResolution(
        replace_actor(action.state, actor_after),
        actor,
        actor_after,
        form_id,
        False,
    )


def resolve_martial_arts_bonus_attack(
    state: CombatState,
) -> BonusStrikeResolution:
    return _resolve_bonus_strikes(
        state,
        feature_id="martial_arts",
        attacks=1,
        ki_cost=0,
    )


def resolve_flurry_of_blows(
    state: CombatState,
) -> BonusStrikeResolution:
    return _resolve_bonus_strikes(
        state,
        feature_id="ki",
        attacks=2,
        ki_cost=1,
    )


def resolve_open_hand_technique(
    state: CombatState,
    *,
    attacker_id: str,
    target_id: str,
    mode: str,
    natural_roll: int | None = None,
    natural_roll_2: int | None = None,
    push_destination: Coordinate | None = None,
) -> OpenHandTechniqueResolution:
    attacker = next(
        (actor for actor in state.actors if str(actor.id) == attacker_id),
        None,
    )
    target = next(
        (actor for actor in state.actors if str(actor.id) == target_id),
        None,
    )
    if attacker is None or target is None:
        raise ValueError("Nieznany uczestnik Open Hand Technique.")
    if not actor_has_feature(attacker, "open_hand_technique"):
        raise ValueError("Atakujący nie posiada Open Hand Technique.")
    if target.is_defeated():
        raise ValueError("Open Hand Technique nie wymaga rozstrzygania dla pokonanego celu.")
    if mode == "no_reactions":
        applied = apply_condition(
            state.condition_states,
            target,
            CombatCondition.NO_REACTIONS,
            source_actor_id=attacker_id,
            source_label="Open Hand Technique",
            duration=EffectDuration.UNTIL_TURN_END,
            expiration_actor_id=attacker_id,
            expiration_event_count=2,
        )
        updated = replace(state, condition_states=applied.condition_states)
        return OpenHandTechniqueResolution(
            updated,
            attacker,
            target,
            target,
            mode,
            None,
            True,
        )
    ability = {"prone": "dexterity", "push": "strength"}.get(mode)
    if ability is None:
        raise ValueError("Nieznany wariant Open Hand Technique.")
    if natural_roll is None:
        raise ValueError("Ten wariant Open Hand Technique wymaga rzutu obronnego.")
    save = resolve_actor_saving_throw(
        target,
        SavingThrowRequest(
            ability=ability,
            dc=open_hand_technique_save_dc(attacker),
            source_label="Open Hand Technique",
            dc_source_label="ST Ki",
        ),
        natural_roll=int(natural_roll),
        natural_roll_2=natural_roll_2,
        condition_states=state.condition_states,
        combat_actors=state.actors,
    )
    if save.success:
        return OpenHandTechniqueResolution(
            state,
            attacker,
            target,
            target,
            mode,
            save,
            False,
        )
    if mode == "prone":
        applied = apply_condition(
            state.condition_states,
            target,
            CombatCondition.PRONE,
            source_actor_id=attacker_id,
            source_label="Open Hand Technique",
        )
        updated = replace(state, condition_states=applied.condition_states)
        target_after = target
    else:
        if push_destination is None:
            raise ValueError("Odepchnięcie Open Hand Technique wymaga legalnego pola końcowego.")
        target_after = replace(target, position=push_destination)
        updated = replace_actor(state, target_after)
    return OpenHandTechniqueResolution(
        updated,
        attacker,
        target,
        target_after,
        mode,
        save,
        True,
        push_destination if mode == "push" else None,
    )


def _resolve_bonus_strikes(
    state: CombatState,
    *,
    feature_id: str,
    attacks: int,
    ki_cost: int,
) -> BonusStrikeResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, feature_id):
        raise ValueError(f"Aktywna postać nie posiada cechy {feature_id}.")
    if feature_id == "martial_arts" and any(
        item.equipped
        and (
            getattr(item, "armor_category", None) is not None
            or item.kind == "shield"
        )
        for item in actor.inventory
    ):
        raise ValueError("Martial Arts wymaga braku pancerza i tarczy.")
    if not state.turn_action.attack_action_active or state.turn_action.attacks_used < 1:
        raise ValueError("Najpierw wykonaj co najmniej jeden atak w akcji Attack.")
    if state.turn_action.bonus_attacks_remaining:
        raise ValueError("Postać ma już oczekujące bonusowe ataki.")
    if ki_cost and not can_spend_actor_resource(actor, "ki_points", ki_cost):
        raise ValueError("Brak punktów Ki.")
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    actor_after = current_actor(action.state)
    if ki_cost:
        spent = spend_actor_resource(actor_after, "ki_points", ki_cost)
        actor_after = spent.actor_after
        updated = replace_actor(action.state, actor_after)
    else:
        updated = action.state
    updated = grant_bonus_attacks(
        updated,
        count=attacks,
        source_id="unarmed_strike",
    )
    return BonusStrikeResolution(
        updated,
        actor,
        actor_after,
        attacks,
        "unarmed_strike",
        ki_cost,
    )


def resolve_divine_sense(
    state: CombatState,
    *,
    board: BoardState | None = None,
) -> DivineSenseResolution:
    """Detect relevant creature types in the encounter without revealing locations."""
    actor = current_actor(state)
    if not actor_has_feature(actor, "divine_sense"):
        raise ValueError("Aktywna postać nie posiada Divine Sense.")
    if not can_spend_actor_resource(actor, "divine_sense_uses"):
        raise ValueError("Brak użyć Divine Sense.")
    action = use_action_economy_cost(state, ActionEconomyCost.ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(
        current_actor(action.state),
        "divine_sense_uses",
    )
    updated = replace_actor(action.state, spent.actor_after)
    detected = tuple(
        sorted(
            {
                target.creature_type
                for target in updated.actors
                if target.id != actor.id
                and not target.is_defeated()
                and target.creature_type in {"celestial", "fiend", "undead"}
                and grid_distance_feet(actor.position, target.position) <= 60
                and (
                    board is None
                    or line_of_sight_clear(board, actor.position, target.position)
                )
            }
        )
    )
    return DivineSenseResolution(updated, actor, spent.actor_after, detected)


def resolve_sacred_weapon(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    weapon_item_id: str = "",
) -> SacredWeaponResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "channel_divinity_sacred_weapon"):
        raise ValueError("Aktywna postać nie posiada Sacred Weapon.")
    weapons = tuple(
        item
        for item in normalize_hand_equipment(actor.inventory)
        if item.kind == "weapon" and item.equipped
    )
    weapon = next(
        (
            item
            for item in weapons
            if item.id == weapon_item_id or item.source_ref == weapon_item_id
        ),
        None,
    )
    if weapon is None and not weapon_item_id and len(weapons) == 1:
        weapon = weapons[0]
    if weapon is None:
        raise ValueError("Wybierz trzymaną broń dla Sacred Weapon.")
    if not can_spend_actor_resource(actor, "channel_divinity_uses"):
        raise ValueError("Brak użyć Channel Divinity.")
    action = use_action_economy_cost(state, ActionEconomyCost.ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(
        current_actor(action.state),
        "channel_divinity_uses",
    )
    updated = replace_actor(action.state, spent.actor_after)
    bonus = max(1, ability_modifier(actor.ability_scores.charisma))
    effect = ActiveEffect(
        id=f"sacred_weapon:{actor.id}",
        actor_id=str(actor.id),
        kind="sacred_weapon_attack_bonus",
        label="Sacred Weapon",
        object_id=f"weapon:{weapon.id}",
        value=bonus,
        source_actor_id=str(actor.id),
        source=EffectSource(
            EffectSourceType.ACTION,
            "channel_divinity_sacred_weapon",
            "Sacred Weapon",
        ),
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )
    effects = apply_active_effect(active_effects, effect).active_effects
    return SacredWeaponResolution(
        updated,
        effects,
        actor,
        spent.actor_after,
        weapon.id,
        bonus,
    )


def resolve_font_of_magic(
    state: CombatState,
    *,
    mode: str,
    slot_level: int,
) -> FontOfMagicResolution:
    """Use the Font of Magic bonus action for either legal conversion."""
    actor = current_actor(state)
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    actor_after_action = current_actor(action.state)
    if mode == "slot_to_points":
        conversion = convert_spell_slot_to_sorcery_points(
            actor_after_action,
            slot_level=slot_level,
        )
    elif mode == "points_to_slot":
        conversion = create_spell_slot_from_sorcery_points(
            actor_after_action,
            slot_level=slot_level,
        )
    else:
        raise ValueError("Nieznany tryb Font of Magic.")
    return FontOfMagicResolution(
        replace_actor(action.state, conversion.actor_after),
        replace(conversion, actor_before=actor),
    )


def resolve_bardic_inspiration(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    target_id: str,
) -> BardicInspirationResolution:
    bard = current_actor(state)
    if not actor_has_feature(bard, "bardic_inspiration"):
        raise ValueError("Aktywna postać nie posiada Bardic Inspiration.")
    target = next(
        (actor for actor in state.actors if str(actor.id) == target_id),
        None,
    )
    if target is None or target.faction != bard.faction or target.id == bard.id:
        raise ValueError("Bardic Inspiration wymaga innego sojusznika.")
    if target.is_defeated() or grid_distance_feet(bard.position, target.position) > 60:
        raise ValueError("Cel Bardic Inspiration jest poza zasięgiem.")
    if any(
        effect.actor_id == target_id and effect.kind == "bardic_inspiration"
        for effect in active_effects
    ):
        raise ValueError("Cel ma już Bardic Inspiration.")
    if not can_spend_actor_resource(bard, "bardic_inspiration_uses"):
        raise ValueError("Brak użyć Bardic Inspiration.")
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(
        current_actor(action.state),
        "bardic_inspiration_uses",
    )
    updated_state = replace_actor(action.state, spent.actor_after)
    die_sides = bardic_inspiration_die_sides(bard)
    effect = ActiveEffect(
        id=f"bardic_inspiration:{bard.id}:{target.id}",
        actor_id=target_id,
        kind="bardic_inspiration",
        label=f"Bardic Inspiration k{die_sides}",
        object_id="class_feature:bardic_inspiration",
        value=die_sides,
        source_actor_id=str(bard.id),
        target_actor_id=target_id,
        source=EffectSource(
            EffectSourceType.ACTION,
            "bardic_inspiration",
            "Bardic Inspiration",
        ),
        # The combat clock has no ten-minute boundary. Encounter end is the
        # conservative tabletop equivalent; scenario-time expiry is documented.
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )
    effects = apply_active_effect(active_effects, effect).active_effects
    return BardicInspirationResolution(
        updated_state,
        effects,
        bard,
        spent.actor_after,
        target,
        die_sides,
    )


def resolve_preserve_life(
    state: CombatState,
    allocations: tuple[PreserveLifeAllocation, ...],
) -> PreserveLifeResolution:
    cleric = current_actor(state)
    validate_preserve_life_allocations(cleric, state.actors, allocations)
    if not allocations:
        raise ValueError("Preserve Life wymaga co najmniej jednego celu.")
    targets_by_id = {str(actor.id): actor for actor in state.actors}
    for allocation in allocations:
        target = targets_by_id[allocation.target_id]
        if target.creature_type in {"undead", "construct"}:
            raise ValueError("Preserve Life nie leczy undead ani construct.")
        if grid_distance_feet(cleric.position, target.position) > 30:
            raise ValueError("Cel Preserve Life jest poza zasięgiem 30 stóp.")
    if not can_spend_actor_resource(cleric, "channel_divinity_uses"):
        raise ValueError("Brak użyć Channel Divinity.")
    action = use_action_economy_cost(state, ActionEconomyCost.ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(
        current_actor(action.state),
        "channel_divinity_uses",
    )
    updated = replace_actor(action.state, spent.actor_after)
    for allocation in allocations:
        target = next(
            actor
            for actor in updated.actors
            if str(actor.id) == allocation.target_id
        )
        updated = replace_actor(
            updated,
            replace(target, hp=min(target.max_hp, target.hp + allocation.healing)),
        )
    cleric_after = next(
        actor for actor in updated.actors if actor.id == cleric.id
    )
    return PreserveLifeResolution(
        updated,
        cleric,
        cleric_after,
        tuple(allocation.target_id for allocation in allocations),
        sum(allocation.healing for allocation in allocations),
    )


def resolve_patient_defense(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> KiDefenseResolution:
    return _resolve_ki_defense(
        state,
        active_effects,
        feature_id="patient_defense",
        effect_kind="dodge_until_next_turn",
        label="Patient Defense",
    )


def resolve_limited_dodge(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    feature_id: str,
    resource_id: str,
    label: str,
) -> LimitedDodgeResolution:
    """Use a short-rest archetype defense without introducing Ki."""

    actor = current_actor(state)
    if not actor_has_feature(actor, feature_id):
        raise ValueError(f"Aktywna postać nie posiada cechy {label}.")
    if not can_spend_actor_resource(actor, resource_id):
        raise ValueError(f"Brak użyć: {label}.")
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(current_actor(action.state), resource_id)
    updated = replace_actor(action.state, spent.actor_after)
    effect = ActiveEffect(
        id=f"dodge_until_next_turn:{actor.id}",
        actor_id=str(actor.id),
        kind="dodge_until_next_turn",
        label=label,
        object_id=f"class_feature:{feature_id}",
        value=0,
        source_actor_id=str(actor.id),
        source=EffectSource(EffectSourceType.ACTION, feature_id, label),
        duration=EffectDuration.UNTIL_TURN_START,
        expiration_actor_id=str(actor.id),
    )
    effects = apply_active_effect(active_effects, effect).active_effects
    return LimitedDodgeResolution(
        updated,
        effects,
        actor,
        spent.actor_after,
        feature_id,
    )


def resolve_archetype_attack_focus(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    feature_id: str,
    resource_id: str,
    label: str,
) -> LimitedDodgeResolution:
    """Spend a curated resource and bonus action for the next attack this turn."""

    actor = current_actor(state)
    if not actor_has_feature(actor, feature_id):
        raise ValueError(f"Aktywna postać nie posiada cechy {label}.")
    if not can_spend_actor_resource(actor, resource_id):
        raise ValueError(f"Brak użyć: {label}.")
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(current_actor(action.state), resource_id)
    updated = replace_actor(action.state, spent.actor_after)
    effect = ActiveEffect(
        id=f"next_attack_advantage:{feature_id}:{actor.id}",
        actor_id=str(actor.id),
        kind="next_attack_advantage",
        label=label,
        object_id=f"class_feature:{feature_id}",
        value=0,
        source_actor_id=str(actor.id),
        source=EffectSource(EffectSourceType.ACTION, feature_id, label),
        duration=EffectDuration.UNTIL_NEXT_ATTACK,
        expiration_actor_id=str(actor.id),
        additional_expirations=(
            AdditionalEffectExpiration(
                EffectDuration.UNTIL_TURN_END,
                actor_id=str(actor.id),
            ),
        ),
    )
    effects = apply_active_effect(active_effects, effect).active_effects
    return LimitedDodgeResolution(
        updated,
        effects,
        actor,
        spent.actor_after,
        feature_id,
    )


def resolve_step_of_the_wind(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> KiDefenseResolution:
    resolution = _resolve_ki_defense(
        state,
        active_effects,
        feature_id="step_of_the_wind",
        effect_kind="disengage_until_turn_end",
        label="Step of the Wind",
    )
    actor = current_actor(resolution.state)
    updated = replace(
        resolution.state,
        turn_action=replace(
            resolution.state.turn_action,
            extra_movement_feet=(
                resolution.state.turn_action.extra_movement_feet
                + actor.speed_feet
            ),
        ),
    )
    return replace(resolution, state=updated)


def _resolve_ki_defense(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    feature_id: str,
    effect_kind: str,
    label: str,
) -> KiDefenseResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "ki"):
        raise ValueError("Aktywna postać nie posiada Ki.")
    if not can_spend_actor_resource(actor, "ki_points"):
        raise ValueError("Brak punktów Ki.")
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(current_actor(action.state), "ki_points")
    updated = replace_actor(action.state, spent.actor_after)
    effect = ActiveEffect(
        id=f"{effect_kind}:{actor.id}",
        actor_id=str(actor.id),
        kind=effect_kind,
        label=label,
        object_id=f"class_feature:{feature_id}",
        value=0,
        source_actor_id=str(actor.id),
        source=EffectSource(EffectSourceType.ACTION, feature_id, label),
        duration=(
            EffectDuration.UNTIL_TURN_START
            if effect_kind == "dodge_until_next_turn"
            else EffectDuration.UNTIL_TURN_END
        ),
        expiration_actor_id=str(actor.id),
    )
    effects = apply_active_effect(active_effects, effect).active_effects
    return KiDefenseResolution(
        updated,
        effects,
        actor,
        spent.actor_after,
        feature_id,
    )


def resolve_action_surge(state: CombatState) -> ActionSurgeResolution:
    """Spend a bonus action and Action Surge to restore the main action."""
    actor = current_actor(state)
    if not actor_has_feature(actor, "action_surge"):
        raise ValueError("Aktywna postać nie posiada cechy Action Surge.")
    if state.turn_action.action_use != ActionUse.ACTION_USED:
        raise ValueError("Action Surge można użyć po wykorzystaniu zwykłej akcji.")
    if not can_spend_actor_resource(actor, "action_surge_uses"):
        raise ValueError("Action Surge zostało już wykorzystane.")
    bonus_action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not bonus_action.accepted:
        raise ValueError(bonus_action.message)
    spent = spend_actor_resource(current_actor(bonus_action.state), "action_surge_uses")
    updated_state = replace_actor(bonus_action.state, spent.actor_after)
    updated_state = replace(
        updated_state,
        turn_action=replace(
            updated_state.turn_action,
            action_use=ActionUse.ACTION_AVAILABLE,
            attack_action_active=False,
            attacks_used=0,
            attacks_maximum=0,
        ),
    )
    return ActionSurgeResolution(updated_state, actor, spent.actor_after)


def resolve_rage(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> RageResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "rage"):
        raise ValueError("Aktywna postać nie posiada cechy Rage.")
    rage_active = any(
        effect.actor_id == str(actor.id) and effect.kind == "rage"
        for effect in active_effects
    )
    if rage_active:
        action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
        if not action.accepted:
            raise ValueError(action.message)
        frenzied = any(
            effect.actor_id == str(actor.id) and effect.kind == "frenzy"
            for effect in active_effects
        )
        actor_after = current_actor(action.state)
        if frenzied:
            actor_after = increase_exhaustion(actor_after)
        actor_after = _set_ferocity(actor_after, 0)
        updated_state = replace_actor(action.state, actor_after)
        updated_effects = tuple(
            effect
            for effect in active_effects
            if not (
                effect.actor_id == str(actor.id)
                and effect.kind
                in {
                    "rage",
                    "rage_duration",
                    "rage_activity",
                    "brakka_acceleration",
                    "powerful_strike",
                    "reckless_attack_advantage",
                    "frenzy",
                    "frenzy_pending",
                }
            )
        )
        return RageResolution(
            updated_state,
            updated_effects,
            actor,
            actor_after,
            False,
            frenzied,
        )
    if not can_spend_actor_resource(actor, "rage_uses"):
        raise ValueError("Brak użyć Rage.")
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    actor_after_action = current_actor(action.state)
    spent = spend_actor_resource(actor_after_action, "rage_uses")
    actor_after = _set_ferocity(
        spent.actor_after,
        max(1, ability_modifier(spent.actor_after.ability_scores.constitution)),
    )
    updated_state = replace_actor(action.state, actor_after)
    effect = ActiveEffect(
        id=f"rage:{actor.id}",
        actor_id=str(actor.id),
        kind="rage",
        label="Rage",
        object_id="class_feature:rage",
        value=2,
        source_actor_id=str(actor.id),
        source=EffectSource(EffectSourceType.ACTION, "rage", "Rage"),
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )
    effects = apply_active_effect(active_effects, effect).active_effects
    effects = apply_active_effect(
        effects,
        ActiveEffect(
            id=f"rage-duration:{actor.id}",
            actor_id=str(actor.id),
            kind="rage_duration",
            label="Czas Rage",
            object_id="class_feature:rage",
            value=state.round_number,
            source_actor_id=str(actor.id),
            source=EffectSource(EffectSourceType.ACTION, "rage", "Rage"),
            duration=EffectDuration.UNTIL_ENCOUNTER_END,
        ),
    ).active_effects
    return RageResolution(
        updated_state,
        effects,
        actor,
        actor_after,
        True,
    )


def resolve_reckless_attack(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> RecklessAttackResolution:
    """Prepare exactly one melee Strength attack with advantage.

    The ordinary attack flow spends the action.  This resolver only marks the
    chosen attack and the exposure created by using the special action.
    """
    actor = current_actor(state)
    if not actor_has_feature(actor, "reckless_attack"):
        raise ValueError("Aktywna postać nie posiada cechy Reckless Attack.")
    if any(
        effect.actor_id == str(actor.id)
        and effect.kind == "reckless_attack_advantage"
        for effect in active_effects
    ):
        raise ValueError("Lekkomyślny atak jest już przygotowany.")
    advantage = ActiveEffect(
        id=f"reckless_attack_advantage:{actor.id}",
        actor_id=str(actor.id),
        kind="reckless_attack_advantage",
        label="Lekkomyślny atak",
        object_id="class_feature:reckless_attack",
        value=0,
        source_actor_id=str(actor.id),
        source=EffectSource(
            EffectSourceType.ACTION,
            "reckless_attack",
            "Reckless Attack",
        ),
        duration=EffectDuration.UNTIL_NEXT_ATTACK,
        expiration_actor_id=str(actor.id),
        additional_expirations=(
            AdditionalEffectExpiration(
                EffectDuration.UNTIL_TURN_END,
                actor_id=str(actor.id),
            ),
        ),
    )
    exposure = ActiveEffect(
        id=f"reckless_attack_exposure:{actor.id}",
        actor_id=str(actor.id),
        kind="reckless_attack_exposure",
        label="Odsłonięta garda",
        object_id="class_feature:reckless_attack",
        value=0,
        source_actor_id=str(actor.id),
        source=EffectSource(
            EffectSourceType.ACTION,
            "reckless_attack",
            "Lekkomyślny atak",
        ),
        duration=EffectDuration.UNTIL_TURN_START,
        expiration_actor_id=str(actor.id),
    )
    effects = apply_active_effect(active_effects, advantage).active_effects
    effects = apply_active_effect(effects, exposure).active_effects
    return RecklessAttackResolution(state, effects, actor)


def resolve_powerful_strike(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> BrakkaFeatureResolution:
    """Spend 2 Ferocity and prepare one melee Strength attack at +10."""

    actor = current_actor(state)
    _require_brakka_rage_feature(actor, active_effects, "powerful_strike")
    if not can_spend_actor_resource(actor, "ferocity_uses", 2):
        raise ValueError("Potężne uderzenie wymaga 2 punktów Dzikości.")
    spent = spend_actor_resource(actor, "ferocity_uses", 2)
    updated = replace_actor(state, spent.actor_after)
    effect = ActiveEffect(
        id=f"powerful_strike:{actor.id}",
        actor_id=str(actor.id),
        kind="powerful_strike",
        label="Potężne uderzenie",
        object_id="class_feature:powerful_strike",
        value=10,
        source_actor_id=str(actor.id),
        source=EffectSource(
            EffectSourceType.ACTION,
            "powerful_strike",
            "Potężne uderzenie",
        ),
        duration=EffectDuration.UNTIL_NEXT_ATTACK,
        expiration_actor_id=str(actor.id),
        additional_expirations=(
            AdditionalEffectExpiration(
                EffectDuration.UNTIL_TURN_END,
                actor_id=str(actor.id),
            ),
        ),
    )
    effects = apply_active_effect(active_effects, effect).active_effects
    return BrakkaFeatureResolution(
        updated,
        effects,
        actor,
        spent.actor_after,
        "powerful_strike",
        2,
    )


def resolve_acceleration(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> BrakkaFeatureResolution:
    """Increase this turn's total movement cap by Brakka's base speed."""

    actor = current_actor(state)
    _require_brakka_rage_feature(actor, active_effects, "acceleration")
    if not can_spend_actor_resource(actor, "ferocity_uses"):
        raise ValueError("Przyspieszenie wymaga 1 punktu Dzikości.")
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    spent = spend_actor_resource(current_actor(action.state), "ferocity_uses")
    updated = replace_actor(action.state, spent.actor_after)
    updated = replace(
        updated,
        turn_action=replace(
            updated.turn_action,
            extra_movement_feet=updated.turn_action.extra_movement_feet + actor.speed_feet,
        ),
    )
    effect = ActiveEffect(
        id=f"brakka_acceleration:{actor.id}",
        actor_id=str(actor.id),
        kind="brakka_acceleration",
        label="Przyspieszenie",
        object_id="class_feature:acceleration",
        value=actor.speed_feet,
        source_actor_id=str(actor.id),
        duration=EffectDuration.UNTIL_TURN_END,
        expiration_actor_id=str(actor.id),
    )
    effects = apply_active_effect(active_effects, effect).active_effects
    return BrakkaFeatureResolution(
        updated,
        effects,
        actor,
        spent.actor_after,
        "acceleration",
        1,
    )


def resolve_hard_as_rock(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    actor_id: str,
    incoming_damage: int,
    die_roll: int,
) -> HardAsRockResolution:
    """Reduce already-resisted damage by 1d12 + Constitution modifier."""

    if not 1 <= die_roll <= 12:
        raise ValueError("Twarda jak skała wymaga wyniku k12 od 1 do 12.")
    if incoming_damage < 0:
        raise ValueError("Obrażenia nie mogą być ujemne.")
    actor = next(
        (candidate for candidate in state.actors if str(candidate.id) == actor_id),
        None,
    )
    if actor is None or not actor_has_feature(actor, "hard_as_rock"):
        raise ValueError("Postać nie posiada cechy Twarda jak skała.")
    _require_active_rage(actor, active_effects)
    if actor.id in state.spent_reaction_actor_ids:
        raise ValueError("Reakcja tej postaci została już wykorzystana.")
    if not can_spend_actor_resource(actor, "ferocity_uses"):
        raise ValueError("Brak punktów Dzikości.")
    spent = spend_actor_resource(actor, "ferocity_uses")
    reduction = die_roll + ability_modifier(actor.ability_scores.constitution)
    updated = replace_actor(state, spent.actor_after)
    updated = replace(
        updated,
        spent_reaction_actor_ids=frozenset((*updated.spent_reaction_actor_ids, actor.id)),
    )
    return HardAsRockResolution(
        updated,
        actor,
        spent.actor_after,
        incoming_damage,
        reduction,
        max(0, incoming_damage - reduction),
        die_roll,
    )


def shoulder_check_push_distance(attacker_total: int, defender_total: int) -> int:
    """Return 0 on a tie/loss, otherwise 5 ft plus 5 per full 5 margin."""

    margin = int(attacker_total) - int(defender_total)
    return 0 if margin <= 0 else min(30, 5 + (margin // 5) * 5)


def legal_shoulder_check_destinations(
    board: BoardState,
    state: CombatState,
    attacker: Actor,
    target: Actor,
    *,
    distance_feet: int,
) -> tuple[Coordinate, ...]:
    """Legal free destinations that do not pull the target toward Brakka."""

    if distance_feet <= 0:
        return ()
    origin_distance = grid_distance_feet(attacker.position, target.position)
    occupied = {
        candidate.position
        for candidate in state.actors
        if candidate.id != target.id and not candidate.is_defeated()
    }
    return tuple(
        position
        for row in range(board.dimensions.rows)
        for col in range(board.dimensions.cols)
        for position in (Coordinate(col, row),)
        if position != target.position
        and position not in occupied
        and not board.terrain_at(position).blocks_movement
        and grid_distance_feet(target.position, position) <= distance_feet
        and grid_distance_feet(attacker.position, position) >= origin_distance
        and line_of_sight_clear(board, target.position, position)
    )


def resolve_shoulder_check(
    state: CombatState,
    *,
    board: BoardState,
    target_id: str,
    attacker_roll: int,
    defender_roll: int,
    destination: Coordinate | None = None,
) -> ShoulderCheckResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "shoulder_check"):
        raise ValueError("Aktywna postać nie posiada zdolności Z bara.")
    target = next((item for item in state.actors if str(item.id) == target_id), None)
    if target is None or target.faction == actor.faction or target.is_defeated():
        raise ValueError("Z bara wymaga żywego przeciwnika.")
    if grid_distance_feet(actor.position, target.position) > 5:
        raise ValueError("Cel Z bara musi znajdować się w odległości 5 stóp.")
    sizes = ("tiny", "small", "medium", "large", "huge", "gargantuan")
    if sizes.index(target.size.value) > sizes.index(actor.size.value) + 1:
        raise ValueError("Cel Z bara jest o więcej niż jeden rozmiar większy.")
    action = use_action_economy_cost(state, ActionEconomyCost.ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    attacker_total = int(attacker_roll) + skill_modifier(actor, "athletics")
    defender_total = int(defender_roll) + skill_modifier(target, "athletics")
    distance = shoulder_check_push_distance(attacker_total, defender_total)
    legal = legal_shoulder_check_destinations(
        board,
        action.state,
        actor,
        target,
        distance_feet=distance,
    )
    if distance == 0 or not legal:
        distance = 0
        destination = target.position
    elif destination not in legal:
        raise ValueError("Wybrane pole nie jest legalnym celem odepchnięcia Z bara.")
    target_after = replace(target, position=destination or target.position)
    updated = replace_actor(action.state, target_after)
    return ShoulderCheckResolution(
        updated,
        actor,
        target,
        target_after,
        attacker_total,
        defender_total,
        distance,
        distance > 0,
    )


def deafening_roar_attack_source(
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...],
) -> AttackSource | None:
    """Build Brakka's 15-foot hostile cone while it is currently usable."""

    if not actor_has_feature(actor, "deafening_roar"):
        return None
    if not any(
        effect.actor_id == str(actor.id) and effect.kind == "rage"
        for effect in active_effects
    ):
        return None
    if not can_spend_actor_resource(actor, "ferocity_uses", 2):
        return None
    area = SpellArea(
        shape=SpellAreaShape.CONE,
        length_feet=15,
        width_feet=15,
        target_mode=SpellAreaTargetMode.ENEMIES,
    )
    return AttackSource(
        id="deafening_roar",
        name="Ogłuszający ryk",
        source_type=AttackSourceType.CUSTOM,
        range_feet=15,
        attack_kind=AttackKind.RANGED,
        attack_roll_request=D20RollRequest(),
        damage_hint="2k6 thunder",
        damage_components=(
            DamageComponentSpec(
                id="deafening_roar",
                damage_type=DamageType.THUNDER,
                dice=DiceExpression(2, 6),
                label="Ogłuszający ryk",
            ),
        ),
        area=area,
        save_ability="constitution",
        save_dc=12 + ability_modifier(actor.ability_scores.constitution),
        save_damage_on_success="half",
        resource_pool_id="ferocity_uses",
        resource_cost=2,
        action_cost=ActionEconomyCost.ACTION,
        tabletop_riders=(
            "Porażka: brak dobrowolnego ruchu do końca najbliższej tury celu.",
            "Naturalne 1: dodatkowo utrudnienie ataków; naturalne 20: bez obrażeń.",
        ),
    )
def _require_brakka_rage_feature(
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...],
    feature_id: str,
) -> None:
    if not actor_has_feature(actor, feature_id):
        raise ValueError("Aktywna postać nie posiada tej zdolności Brakki.")
    _require_active_rage(actor, active_effects)


def _require_active_rage(
    actor: Actor,
    active_effects: tuple[ActiveEffect, ...],
) -> None:
    if not any(
        effect.actor_id == str(actor.id) and effect.kind == "rage"
        for effect in active_effects
    ):
        raise ValueError("Ta zdolność wymaga aktywnego Szału.")


def _set_ferocity(actor: Actor, current: int) -> Actor:
    pool = actor_resource_pool(actor, "ferocity_uses")
    if pool is None:
        return actor
    bounded = max(0, min(pool.maximum, current))
    return replace(
        actor,
        resource_pools=tuple(
            replace(candidate, current=bounded)
            if candidate.id == "ferocity_uses"
            else candidate
            for candidate in actor.resource_pools
        ),
    )


def apply_life_domain_to_healing_source(
    actor: Actor,
    source: HealingSource,
) -> HealingSource:
    """Apply the 2014 Life Domain's Disciple of Life to a leveled healing spell."""
    if (
        not actor_has_feature(actor, "disciple_of_life")
        or source.source_type != HealingSourceType.SPELL
        or source.spell_level < 1
    ):
        return source
    modifier = source.healing_modifier + 2 + source.spell_level
    hint = source.healing_hint
    if hint:
        hint = f"{hint} + {2 + source.spell_level} (Disciple of Life)"
    return replace(
        source,
        healing_modifier=modifier,
        healing_modifier_per_cast_level=(
            source.healing_modifier_per_cast_level + 1
        ),
        healing_hint=hint,
    )


def resolve_second_wind(
    state: CombatState,
    natural_roll: int,
) -> SecondWindResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "second_wind"):
        raise ValueError("Aktywna postać nie posiada cechy Second Wind.")
    if not 1 <= natural_roll <= 10:
        raise ValueError("Wynik Second Wind musi mieścić się w zakresie 1–10.")
    if not can_spend_actor_resource(actor, "second_wind_uses"):
        raise ValueError("Second Wind zostało już wykorzystane.")
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    actor_after_action = current_actor(action.state)
    spent = spend_actor_resource(actor_after_action, "second_wind_uses")
    source = HealingSource(
        id="second_wind",
        name="Second Wind",
        source_type=HealingSourceType.CUSTOM,
        range_feet=5,
        healing_hint=f"1d10 + {actor.level}",
        healing_die_sides=10,
        healing_modifier=actor.level,
        action_cost=ActionEconomyCost.BONUS_ACTION,
    )
    healing = apply_healing_result(
        spent.actor_after,
        source,
        natural_roll + actor.level,
        condition_states=action.state.condition_states,
    )
    updated_state = replace_actor(action.state, healing.actor_after)
    return SecondWindResolution(
        state=updated_state,
        actor_before=actor,
        actor_after=healing.actor_after,
        healing=healing,
        natural_roll=natural_roll,
    )


def resolve_lay_on_hands(
    state: CombatState,
    target_id: str,
    points: int,
) -> LayOnHandsResolution:
    """Spend a Paladin action and any positive part of the Lay on Hands pool."""
    healer = current_actor(state)
    if not actor_has_feature(healer, "lay_on_hands"):
        raise ValueError("Aktywna postać nie posiada cechy Lay on Hands.")
    if points < 1:
        raise ValueError("Lay on Hands musi wydać co najmniej 1 punkt.")
    if not can_spend_actor_resource(healer, "lay_on_hands_points", points):
        raise ValueError("Brak wystarczającej liczby punktów Lay on Hands.")
    target = next(
        (candidate for candidate in state.actors if str(candidate.id) == target_id),
        None,
    )
    if target is None:
        raise ValueError(f"Nieznany cel Lay on Hands: {target_id}.")
    if target.is_dead():
        raise ValueError("Lay on Hands nie może przywrócić martwej istoty.")
    if grid_distance_feet(healer.position, target.position) > 5:
        raise ValueError("Cel Lay on Hands musi znajdować się w zasięgu dotyku.")
    action = use_action_economy_cost(state, ActionEconomyCost.ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    healer_after_action = current_actor(action.state)
    spent = spend_actor_resource(
        healer_after_action,
        "lay_on_hands_points",
        points,
    )
    state_after_spend = replace_actor(action.state, spent.actor_after)
    target_after_spend = (
        spent.actor_after
        if target.id == healer.id
        else next(
            candidate
            for candidate in state_after_spend.actors
            if candidate.id == target.id
        )
    )
    source = HealingSource(
        id="lay_on_hands",
        name="Lay on Hands",
        source_type=HealingSourceType.CUSTOM,
        range_feet=5,
        healing_hint=str(points),
        healing_fixed=points,
        action_cost=ActionEconomyCost.ACTION,
    )
    healing = apply_healing_result(
        target_after_spend,
        source,
        points,
        condition_states=state_after_spend.condition_states,
    )
    updated_state = replace_actor(state_after_spend, healing.actor_after)
    healer_after = next(
        candidate for candidate in updated_state.actors if candidate.id == healer.id
    )
    return LayOnHandsResolution(
        state=updated_state,
        healer_before=healer,
        healer_after=healer_after,
        target_before=target,
        target_after=healing.actor_after,
        healing=healing,
        points_spent=points,
    )


@dataclass(frozen=True, slots=True)
class SneakAttackPlan:
    eligible: bool
    reason: str
    source: AttackSource


def plan_sneak_attack(
    *,
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    attacker: Actor,
    target: Actor,
    source: AttackSource,
    roll_mode: RollMode,
) -> SneakAttackPlan:
    mira_killer = actor_has_feature(attacker, "mira_shadow_killer")
    if not actor_has_feature(attacker, "sneak_attack") and not mira_killer:
        return SneakAttackPlan(False, "Postać nie posiada cechy Sneak Attack.", source)
    if target.faction == attacker.faction:
        return SneakAttackPlan(False, "Sneak Attack wymaga wrogiego celu.", source)
    if any(
        effect.kind == "sneak_attack_used"
        and effect.actor_id == str(attacker.id)
        for effect in active_effects
    ):
        return SneakAttackPlan(False, "Sneak Attack wykorzystano już w tej turze.", source)
    if not mira_killer and not _sneak_attack_weapon_is_eligible(attacker, source):
        return SneakAttackPlan(False, "Sneak Attack wymaga broni finesse albo ataku dystansowego.", source)
    if roll_mode == RollMode.DISADVANTAGE:
        return SneakAttackPlan(False, "Sneak Attack nie działa przy disadvantage.", source)
    modifier_keys = {
        modifier.stacking_key
        for modifier in source.attack_roll_request.modifiers
    }
    hidden_attack = "hidden_attacker_advantage" in modifier_keys
    mira_flank = "flanking_advantage" in modifier_keys
    if mira_killer:
        weapon_name = source.name.casefold()
        eligible_weapon = (
            source.source_type == AttackSourceType.WEAPON
            and (
                "rapier" in weapon_name
                or "nóż do rzucania" in weapon_name
                or "throwing_knife" in source.id
                or source.source_item_id in {"rapier", "throwing_knife"}
                or source.proficiency_id in {"rapier", "throwing_knife"}
            )
        )
        if not eligible_weapon:
            return SneakAttackPlan(
                False,
                "Premia Miry wymaga rapiera albo noża do rzucania.",
                source,
            )
        sneak_attack_dice = (2 if hidden_attack else 0) + (1 if mira_flank else 0)
        if sneak_attack_dice <= 0:
            return SneakAttackPlan(
                False,
                "Mira musi atakować z ukrycia lub osobiście flankować cel.",
                source,
            )
        return SneakAttackPlan(
            True,
            f"Premia zabójczyni {sneak_attack_dice}d6 jest dostępna.",
            sneak_attack_source_with_dice(source, sneak_attack_dice),
        )
    has_adjacent_ally = any(
        other.id != attacker.id
        and other.faction == attacker.faction
        and not other.is_defeated()
        and grid_distance_feet(other.position, target.position) <= 5
        for other in state.actors
    )
    if roll_mode != RollMode.ADVANTAGE and not has_adjacent_ally:
        return SneakAttackPlan(
            False,
            "Potrzebujesz advantage albo sojusznika przy celu.",
            source,
        )
    sneak_attack_dice = (attacker.level + 1) // 2
    component = DamageComponentSpec(
        id="sneak_attack",
        damage_type=DamageType(source.damage_type),
        dice=DiceExpression(sneak_attack_dice, 6),
        label="Sneak Attack",
    )
    enhanced = replace(
        source,
        damage_components=(*source.damage_components, component),
        damage_hint=(
            f"{source.damage_hint} + {component.hint()}".strip(" +")
        ),
    )
    return SneakAttackPlan(
        True,
        f"Sneak Attack {sneak_attack_dice}d6 jest dostępny.",
        enhanced,
    )


def sneak_attack_source_with_dice(
    source: AttackSource,
    dice_count: int,
) -> AttackSource:
    component = DamageComponentSpec(
        id="sneak_attack",
        damage_type=DamageType(source.damage_type),
        dice=DiceExpression(dice_count, 6),
        label="Atak z ukrycia / flanki",
    )
    return replace(
        source,
        damage_components=(*source.damage_components, component),
        damage_hint=f"{source.damage_hint} + {component.hint()}".strip(" +"),
    )


def commit_sneak_attack_hit(
    active_effects: tuple[ActiveEffect, ...],
    actor_id: str,
) -> tuple[ActiveEffect, ...]:
    marker = ActiveEffect(
        id=f"sneak_attack_used:{actor_id}",
        actor_id=actor_id,
        kind="sneak_attack_used",
        label="Sneak Attack wykorzystany",
        object_id="class_feature:sneak_attack",
        value=1,
        source_actor_id=actor_id,
        source=EffectSource(
            EffectSourceType.ACTION,
            "sneak_attack",
            "Sneak Attack",
        ),
        duration=EffectDuration.UNTIL_TURN_START,
    )
    return apply_active_effect(active_effects, marker).active_effects


def commit_colossus_slayer_hit(
    active_effects: tuple[ActiveEffect, ...],
    actor_id: str,
) -> tuple[ActiveEffect, ...]:
    marker = ActiveEffect(
        id=f"colossus_slayer_used:{actor_id}",
        actor_id=actor_id,
        kind="colossus_slayer_used",
        label="Colossus Slayer wykorzystany",
        object_id="class_feature:colossus_slayer",
        value=1,
        source_actor_id=actor_id,
        source=EffectSource(
            EffectSourceType.ACTION,
            "colossus_slayer",
            "Colossus Slayer",
        ),
        duration=EffectDuration.UNTIL_TURN_START,
    )
    return apply_active_effect(active_effects, marker).active_effects


def _sneak_attack_weapon_is_eligible(
    actor: Actor,
    source: AttackSource,
) -> bool:
    if source.source_type != AttackSourceType.WEAPON:
        return False
    if source.attack_kind == AttackKind.RANGED:
        return True
    if source.source_item_id is None:
        return False
    item = next(
        (
            candidate
            for candidate in normalize_hand_equipment(actor.inventory)
            if candidate.id == source.source_item_id
            or candidate.source_ref == source.source_item_id
        ),
        None,
    )
    return item is not None and WeaponProperty.FINESSE in item.weapon_properties
