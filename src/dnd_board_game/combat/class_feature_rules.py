"""Deterministic D&D 5e 2014 class-feature rules through character level 3."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorSenseProfile,
    CreatureSize,
    DamageAffinityProfile,
    WildShapeState,
    attack_roll_modifiers,
    actor_has_feature,
    actor_resource_pool,
    can_spend_actor_resource,
    spend_actor_resource,
)
from dnd_board_game.rules import (
    D20RollRequest,
    DiceExpression,
    RollModifier,
    RollModifierType,
    SpellDurationKind,
    SpellRangeKind,
    ability_modifier,
)

from .action_economy import ActionEconomyCost
from .attack_flow import AttackKind, AttackSource, AttackSourceType
from .damage import DamageComponentSpec, DamageType
from .healing import HealingSource, HealingSourceType
from .spells import SpellSlotState


@dataclass(frozen=True, slots=True)
class WildShapeLimits:
    maximum_challenge_rating: float
    swimming_allowed: bool
    flying_allowed: bool
    duration_hours: int


@dataclass(frozen=True, slots=True)
class JumpDistances:
    running_long_jump_feet: int
    standing_long_jump_feet: int
    running_high_jump_feet: int
    standing_high_jump_feet: int


@dataclass(frozen=True, slots=True)
class WildShapeForm:
    id: str
    name: str
    challenge_rating: float
    ac: int
    hit_points: int
    speed_feet: int
    ability_scores: AbilityScores
    size: CreatureSize
    attack_name: str
    attack_damage_dice: DiceExpression | None
    attack_damage_type: DamageType
    attack_damage_fixed: int | None = None
    attack_damage_modifier: int = 0
    attack_ability: str = "strength"
    darkvision_feet: int = 0
    has_swimming_speed: bool = False
    has_flying_speed: bool = False


WILD_SHAPE_FORMS: tuple[WildShapeForm, ...] = (
    WildShapeForm(
        "badger", "Borsuk", 0.0, 10, 3, 20,
        AbilityScores(4, 11, 12, 2, 12, 5), CreatureSize.TINY,
        "Ugryzienie", None, DamageType.PIERCING, attack_damage_fixed=1,
        darkvision_feet=30,
    ),
    WildShapeForm(
        "cat", "Kot", 0.0, 12, 2, 40,
        AbilityScores(3, 15, 10, 3, 12, 7), CreatureSize.TINY,
        "Pazury", None, DamageType.SLASHING, attack_damage_fixed=1,
    ),
    WildShapeForm(
        "deer", "Jeleń", 0.0, 13, 4, 50,
        AbilityScores(11, 16, 11, 2, 14, 5), CreatureSize.MEDIUM,
        "Ugryzienie", DiceExpression(1, 4), DamageType.PIERCING,
    ),
    WildShapeForm(
        "mastiff", "Mastif", 0.125, 12, 5, 40,
        AbilityScores(13, 14, 12, 3, 12, 7), CreatureSize.MEDIUM,
        "Ugryzienie", DiceExpression(1, 6), DamageType.PIERCING,
        attack_damage_modifier=1,
    ),
    WildShapeForm(
        "panther", "Pantera", 0.25, 12, 13, 50,
        AbilityScores(14, 15, 10, 3, 14, 7), CreatureSize.MEDIUM,
        "Ugryzienie", DiceExpression(1, 6), DamageType.PIERCING,
        attack_damage_modifier=2,
    ),
    WildShapeForm(
        "giant_rat", "Olbrzymi szczur", 0.125, 12, 7, 30,
        AbilityScores(7, 15, 11, 2, 10, 4), CreatureSize.SMALL,
        "Ugryzienie", DiceExpression(1, 4), DamageType.PIERCING,
        attack_damage_modifier=2,
        darkvision_feet=60,
    ),
    WildShapeForm(
        "riding_horse", "Koń wierzchowy", 0.25, 10, 13, 60,
        AbilityScores(16, 10, 12, 2, 11, 7), CreatureSize.LARGE,
        "Kopyta", DiceExpression(2, 4), DamageType.BLUDGEONING,
        attack_damage_modifier=3,
    ),
    WildShapeForm(
        "wolf", "Wilk", 0.25, 13, 11, 40,
        AbilityScores(12, 15, 12, 3, 12, 6), CreatureSize.MEDIUM,
        "Ugryzienie", DiceExpression(2, 4), DamageType.PIERCING,
        attack_damage_modifier=1,
    ),
)


def available_wild_shape_forms(actor: Actor) -> tuple[WildShapeForm, ...]:
    limits = wild_shape_limits(actor)
    return tuple(
        form
        for form in WILD_SHAPE_FORMS
        if form.challenge_rating <= limits.maximum_challenge_rating
        and (limits.swimming_allowed or not form.has_swimming_speed)
        and (limits.flying_allowed or not form.has_flying_speed)
    )


def wild_shape_form(form_id: str) -> WildShapeForm:
    form = next((form for form in WILD_SHAPE_FORMS if form.id == form_id), None)
    if form is None:
        raise ValueError(f"Nieznana forma Wild Shape: {form_id}.")
    return form


def transform_into_wild_shape(actor: Actor, form_id: str) -> Actor:
    if actor.wild_shape is not None:
        raise ValueError("Postać jest już w formie Wild Shape.")
    form = wild_shape_form(form_id)
    if form not in available_wild_shape_forms(actor):
        raise ValueError("Ta forma przekracza aktualne ograniczenia Wild Shape.")
    limits = wild_shape_limits(actor)
    state = WildShapeState(
        form_id=form.id,
        form_name=form.name,
        original_ac=actor.ac,
        original_hp=actor.hp,
        original_max_hp=actor.max_hp,
        original_speed_feet=actor.speed_feet,
        original_ability_scores=actor.ability_scores,
        original_size=actor.size,
        original_senses=actor.senses,
        original_damage_affinities=actor.damage_affinities,
        original_creature_type=actor.creature_type,
        remaining_minutes=limits.duration_hours * 60,
    )
    mental = actor.ability_scores
    physical = form.ability_scores
    return replace(
        actor,
        ac=form.ac,
        hp=form.hit_points,
        max_hp=form.hit_points,
        speed_feet=form.speed_feet,
        ability_scores=AbilityScores(
            physical.strength,
            physical.dexterity,
            physical.constitution,
            mental.intelligence,
            mental.wisdom,
            mental.charisma,
        ),
        size=form.size,
        senses=ActorSenseProfile(darkvision_feet=form.darkvision_feet),
        damage_affinities=DamageAffinityProfile(),
        creature_type="beast",
        wild_shape=state,
    )


def revert_wild_shape(actor: Actor) -> Actor:
    state = actor.wild_shape
    if state is None:
        raise ValueError("Postać nie jest w formie Wild Shape.")
    return replace(
        actor,
        ac=state.original_ac,
        hp=state.original_hp,
        max_hp=state.original_max_hp,
        speed_feet=state.original_speed_feet,
        ability_scores=state.original_ability_scores,
        size=state.original_size,
        senses=state.original_senses,
        damage_affinities=state.original_damage_affinities,
        creature_type=state.original_creature_type,
        wild_shape=None,
    )


def wild_shape_attack_source(actor: Actor) -> AttackSource | None:
    if actor.wild_shape is None:
        return None
    form = wild_shape_form(actor.wild_shape.form_id)
    return AttackSource(
        id=f"wild_shape:{form.id}",
        name=form.attack_name,
        source_type=AttackSourceType.CUSTOM,
        range_feet=5,
        reach_feet=5,
        attack_kind=AttackKind.MELEE,
        attack_roll_request=D20RollRequest(
            modifiers=attack_roll_modifiers(
                actor,
                form.attack_ability,
                proficient=True,
            )
        ),
        damage_fixed=form.attack_damage_fixed,
        damage_die_sides=(
            form.attack_damage_dice.sides
            if form.attack_damage_dice is not None
            and form.attack_damage_dice.count == 1
            else None
        ),
        damage_components=(
            (
                DamageComponentSpec(
                    id=f"wild_shape:{form.id}:damage",
                    damage_type=form.attack_damage_type,
                    dice=form.attack_damage_dice,
                    modifier=form.attack_damage_modifier,
                    label=form.attack_name,
                ),
            )
            if form.attack_damage_dice is not None
            and form.attack_damage_dice.count > 1
            else ()
        ),
        damage_modifier=form.attack_damage_modifier,
        damage_type=form.attack_damage_type.value,
        ability=form.attack_ability,
        damage_hint=(
            f"{form.attack_damage_dice.format()}"
            f"{form.attack_damage_modifier:+d}"
            if form.attack_damage_dice is not None
            else str(form.attack_damage_fixed)
        ),
    )


@dataclass(frozen=True, slots=True)
class DeflectMissilesResult:
    reduction: int
    damage_after_reduction: int
    caught: bool
    can_return_projectile: bool


@dataclass(frozen=True, slots=True)
class PreserveLifeAllocation:
    target_id: str
    healing: int


@dataclass(frozen=True, slots=True)
class FontOfMagicConversion:
    actor_before: Actor
    actor_after: Actor
    mode: str
    slot_level: int
    sorcery_points_changed: int


def bardic_inspiration_die_sides(actor: Actor) -> int:
    _require_feature(actor, "bardic_inspiration")
    return 6 if actor.level <= 4 else 8 if actor.level <= 9 else 10 if actor.level <= 14 else 12


def song_of_rest_die_sides(actor: Actor) -> int:
    _require_feature(actor, "song_of_rest")
    return 6 if actor.level <= 8 else 8 if actor.level <= 12 else 10 if actor.level <= 16 else 12


def wild_shape_limits(actor: Actor) -> WildShapeLimits:
    _require_feature(actor, "wild_shape")
    return WildShapeLimits(
        maximum_challenge_rating=0.25 if actor.level < 4 else 0.5 if actor.level < 8 else 1.0,
        swimming_allowed=actor.level >= 4,
        flying_allowed=actor.level >= 8,
        duration_hours=max(1, actor.level // 2),
    )


def natural_recovery_capacity(actor: Actor) -> int:
    """Combined slot levels recoverable by Circle of the Land on a short rest."""
    _require_feature(actor, "natural_recovery")
    return max(1, ceil(actor.level / 2))


def divine_smite_damage(
    actor: Actor,
    *,
    slot_level: int,
    target_creature_type: str,
) -> DamageComponentSpec:
    _require_feature(actor, "divine_smite")
    if slot_level < 1:
        raise ValueError("Divine Smite wymaga slotu co najmniej 1. poziomu.")
    dice_count = min(5, 1 + slot_level)
    if target_creature_type in {"fiend", "undead"}:
        dice_count += 1
    return DamageComponentSpec(
        id="divine_smite",
        damage_type=DamageType.RADIANT,
        dice=DiceExpression(dice_count, 8),
        label="Divine Smite",
    )


def preserve_life_capacity(actor: Actor) -> int:
    _require_feature(actor, "channel_divinity_preserve_life")
    return actor.level * 5


def validate_preserve_life_allocations(
    actor: Actor,
    targets: tuple[Actor, ...],
    allocations: tuple[PreserveLifeAllocation, ...],
) -> None:
    capacity = preserve_life_capacity(actor)
    if sum(allocation.healing for allocation in allocations) > capacity:
        raise ValueError("Przydział Preserve Life przekracza pulę leczenia.")
    targets_by_id = {str(target.id): target for target in targets}
    if len({allocation.target_id for allocation in allocations}) != len(allocations):
        raise ValueError("Cel Preserve Life może wystąpić tylko raz.")
    for allocation in allocations:
        target = targets_by_id.get(allocation.target_id)
        if target is None:
            raise ValueError(f"Nieznany cel Preserve Life: {allocation.target_id}.")
        if allocation.healing < 1:
            raise ValueError("Przydział Preserve Life musi być dodatni.")
        maximum_healing = max(0, target.max_hp // 2 - target.hp)
        if allocation.healing > maximum_healing:
            raise ValueError(
                "Preserve Life nie może podnieść celu powyżej połowy maksymalnych PW."
            )


def deflect_missiles(
    actor: Actor,
    *,
    natural_d10: int,
    incoming_damage: int,
    has_free_hand: bool,
) -> DeflectMissilesResult:
    _require_feature(actor, "deflect_missiles")
    if not 1 <= natural_d10 <= 10:
        raise ValueError("Deflect Missiles wymaga wyniku k10 od 1 do 10.")
    if incoming_damage < 0:
        raise ValueError("Obrażenia nie mogą być ujemne.")
    reduction = natural_d10 + ability_modifier(actor.ability_scores.dexterity) + actor.level
    remaining = max(0, incoming_damage - reduction)
    caught = remaining == 0 and has_free_hand
    return DeflectMissilesResult(
        reduction=reduction,
        damage_after_reduction=remaining,
        caught=caught,
        can_return_projectile=caught,
    )


def deflected_missile_attack_source(
    actor: Actor,
    *,
    damage_type: DamageType,
) -> AttackSource:
    """Build the special 20/60-foot monk-weapon attack for a caught missile."""

    _require_feature(actor, "deflect_missiles")
    dexterity_modifier = ability_modifier(actor.ability_scores.dexterity)
    return AttackSource(
        name="Odrzucony pocisk",
        source_type=AttackSourceType.WEAPON,
        range_feet=20,
        long_range_feet=60,
        attack_kind=AttackKind.RANGED,
        attack_roll_request=D20RollRequest(
            modifiers=attack_roll_modifiers(
                actor,
                "dexterity",
                proficient=True,
            ),
        ),
        damage_die_sides=4,
        damage_modifier=dexterity_modifier,
        damage_type=damage_type.value,
        damage_components=(
            DamageComponentSpec(
                id="base",
                label="Odrzucony pocisk",
                damage_type=damage_type,
                dice=DiceExpression(1, 4),
                modifier=dexterity_modifier,
            ),
        ),
        id="deflected_missile",
        ability="dexterity",
        proficiency_id="monk_weapon",
    )


def open_hand_technique_save_dc(actor: Actor) -> int:
    _require_feature(actor, "open_hand_technique")
    return 8 + actor.proficiency_bonus + ability_modifier(actor.ability_scores.wisdom)


def jump_distances(actor: Actor) -> JumpDistances:
    strength = max(0, actor.ability_scores.strength)
    running_long = strength
    running_high = max(0, 3 + ability_modifier(strength))
    if actor_has_feature(actor, "second_story_work"):
        bonus = max(0, ability_modifier(actor.ability_scores.dexterity))
        running_long += bonus
        running_high += bonus
    return JumpDistances(
        running_long_jump_feet=running_long,
        standing_long_jump_feet=running_long // 2,
        running_high_jump_feet=running_high,
        standing_high_jump_feet=running_high // 2,
    )


def climbing_movement_cost(actor: Actor, distance_feet: int) -> int:
    if distance_feet < 0:
        raise ValueError("Dystans wspinaczki nie może być ujemny.")
    return (
        distance_feet
        if actor_has_feature(actor, "second_story_work")
        else distance_feet * 2
    )


def sorcery_point_cost_for_slot(slot_level: int) -> int:
    try:
        return {1: 2, 2: 3, 3: 5, 4: 6, 5: 7}[slot_level]
    except KeyError as exc:
        raise ValueError("Można tworzyć wyłącznie sloty poziomów 1–5.") from exc


def sorcery_points_from_slot(slot_level: int) -> int:
    if not 1 <= slot_level <= 9:
        raise ValueError("Poziom slotu musi mieścić się w zakresie 1–9.")
    return slot_level


def convert_spell_slot_to_sorcery_points(
    actor: Actor,
    *,
    slot_level: int,
) -> FontOfMagicConversion:
    """Convert one available slot into sorcery points, respecting the point cap."""
    _require_feature(actor, "font_of_magic")
    points = sorcery_points_from_slot(slot_level)
    pool = actor_resource_pool(actor, "sorcery_points")
    if pool is None:
        raise ValueError("Postać nie ma puli Sorcery Points.")
    if pool.current + points > pool.maximum:
        raise ValueError("Konwersja przekroczyłaby maksymalną pulę Sorcery Points.")
    slot_index = next(
        (
            index
            for index, slot in enumerate(actor.spell_slots)
            if slot.level == slot_level and slot.remaining > 0
        ),
        None,
    )
    if slot_index is None:
        raise ValueError(f"Brak dostępnego slotu {slot_level}. poziomu.")
    slots = list(actor.spell_slots)
    slot = slots[slot_index]
    if slot.temporary and slot.remaining == 1:
        slots.pop(slot_index)
    else:
        slots[slot_index] = replace(slot, remaining=slot.remaining - 1)
    resources = tuple(
        replace(candidate, current=candidate.current + points)
        if candidate.id == "sorcery_points"
        else candidate
        for candidate in actor.resource_pools
    )
    updated = replace(actor, spell_slots=tuple(slots), resource_pools=resources)
    return FontOfMagicConversion(actor, updated, "slot_to_points", slot_level, points)


def create_spell_slot_from_sorcery_points(
    actor: Actor,
    *,
    slot_level: int,
) -> FontOfMagicConversion:
    """Create a temporary slot that disappears at the next long rest."""
    _require_feature(actor, "font_of_magic")
    cost = sorcery_point_cost_for_slot(slot_level)
    if not can_spend_actor_resource(actor, "sorcery_points", cost):
        raise ValueError("Brak Sorcery Points do utworzenia slotu.")
    spent = spend_actor_resource(actor, "sorcery_points", cost)
    temporary_slot = SpellSlotState(
        level=slot_level,
        remaining=1,
        maximum=1,
        recovery="long_rest",
        temporary=True,
    )
    updated = replace(
        spent.actor_after,
        spell_slots=(*spent.actor_after.spell_slots, temporary_slot),
    )
    return FontOfMagicConversion(actor, updated, "points_to_slot", slot_level, -cost)


def metamagic_sorcery_point_cost(feature_id: str, *, spell_level: int = 0) -> int:
    if feature_id == "metamagic_heightened":
        return 3
    if feature_id == "metamagic_quickened":
        return 2
    if feature_id == "metamagic_twinned":
        return max(1, spell_level)
    if feature_id in {
        "metamagic_careful",
        "metamagic_distant",
        "metamagic_empowered",
        "metamagic_extended",
        "metamagic_subtle",
    }:
        return 1
    raise ValueError(f"Nieznana opcja Metamagic: {feature_id}.")


METAMAGIC_FEATURE_IDS: tuple[str, ...] = (
    "metamagic_careful",
    "metamagic_distant",
    "metamagic_empowered",
    "metamagic_extended",
    "metamagic_heightened",
    "metamagic_quickened",
    "metamagic_subtle",
    "metamagic_twinned",
)


@dataclass(frozen=True, slots=True)
class MetamagicOption:
    id: str
    name: str
    sorcery_point_cost: int


_METAMAGIC_NAMES = {
    "metamagic_careful": "Careful Spell",
    "metamagic_distant": "Distant Spell",
    "metamagic_empowered": "Empowered Spell",
    "metamagic_extended": "Extended Spell",
    "metamagic_heightened": "Heightened Spell",
    "metamagic_quickened": "Quickened Spell",
    "metamagic_subtle": "Subtle Spell",
    "metamagic_twinned": "Twinned Spell",
}


def metamagic_options_for_source(
    actor: Actor,
    source: AttackSource | HealingSource,
) -> tuple[MetamagicOption, ...]:
    """Return selected and currently legal 2014 Metamagic choices for a spell source."""
    if not _is_spell_source(source):
        return ()
    spell = next((candidate for candidate in actor.spells if candidate.id == source.id), None)
    if spell is None:
        return ()
    options: list[MetamagicOption] = []
    for feature_id in METAMAGIC_FEATURE_IDS:
        if not actor_has_feature(actor, feature_id):
            continue
        if not _metamagic_is_compatible(feature_id, source, spell):
            continue
        cost = metamagic_sorcery_point_cost(
            feature_id,
            spell_level=int(source.cast_level or source.spell_level),
        )
        if can_spend_actor_resource(actor, "sorcery_points", cost):
            options.append(MetamagicOption(feature_id, _METAMAGIC_NAMES[feature_id], cost))
    return tuple(options)


def apply_metamagic_to_source(
    actor: Actor,
    source: AttackSource | HealingSource,
    metamagic_ids: tuple[str, ...] | list[str],
    *,
    validate_resources: bool = True,
) -> AttackSource | HealingSource:
    """Validate and apply one Metamagic option, optionally combined with Empowered Spell."""
    selected = tuple(dict.fromkeys(str(value) for value in metamagic_ids if str(value)))
    if not selected:
        return source
    unknown = set(selected) - set(METAMAGIC_FEATURE_IDS)
    if unknown:
        raise ValueError(f"Nieznana opcja Metamagic: {sorted(unknown)[0]}.")
    if len(selected) > 1 and (
        len(selected) != 2 or "metamagic_empowered" not in selected
    ):
        raise ValueError(
            "Do jednego czaru można użyć tylko jednej opcji Metamagic; "
            "Empowered Spell może być połączone z jedną inną opcją."
        )
    spell = next(
        (candidate for candidate in actor.spells if candidate.id == source.id),
        None,
    )
    if spell is None:
        raise ValueError("Metamagic działa wyłącznie na znany czar.")
    legal = {
        feature_id
        for feature_id in METAMAGIC_FEATURE_IDS
        if actor_has_feature(actor, feature_id)
        and _metamagic_is_compatible(feature_id, source, spell)
    }
    illegal = set(selected) - legal
    if illegal:
        feature_id = sorted(illegal)[0]
        if not actor_has_feature(actor, feature_id):
            raise ValueError(f"Postać nie zna opcji {_METAMAGIC_NAMES[feature_id]}.")
        raise ValueError(
            f"Opcja {_METAMAGIC_NAMES[feature_id]} nie działa z czarem {source.name}."
        )
    spell_level = int(source.cast_level or source.spell_level)
    cost = sum(
        metamagic_sorcery_point_cost(feature_id, spell_level=spell_level)
        for feature_id in selected
    )
    if (
        validate_resources
        and not can_spend_actor_resource(actor, "sorcery_points", cost)
    ):
        raise ValueError(f"Brak {cost} Sorcery Points na wybrane Metamagic.")

    range_feet = source.range_feet
    action_cost = source.action_cost
    duration_multiplier = source.duration_multiplier
    if "metamagic_distant" in selected:
        range_feet = (
            30
            if spell.range.kind == SpellRangeKind.TOUCH
            else max(range_feet, spell.range.feet) * 2
        )
    if "metamagic_quickened" in selected:
        action_cost = ActionEconomyCost.BONUS_ACTION
    if "metamagic_extended" in selected:
        duration_multiplier = 2
    return replace(
        source,
        range_feet=range_feet,
        action_cost=action_cost,
        duration_multiplier=duration_multiplier,
        metamagic_ids=selected,
        resource_pool_id="sorcery_points",
        resource_cost=cost,
    )


def metamagic_options_for_combat_action(
    actor: Actor,
    action: object,
) -> tuple[MetamagicOption, ...]:
    spell = next(
        (candidate for candidate in actor.spells if candidate.id == getattr(action, "id", "")),
        None,
    )
    if spell is None:
        return ()
    options: list[MetamagicOption] = []
    for feature_id in METAMAGIC_FEATURE_IDS:
        if (
            actor_has_feature(actor, feature_id)
            and _metamagic_is_compatible_with_action(feature_id, action, spell)
        ):
            cost = metamagic_sorcery_point_cost(
                feature_id,
                spell_level=int(getattr(action, "spell_level", 0)),
            )
            if can_spend_actor_resource(actor, "sorcery_points", cost):
                options.append(
                    MetamagicOption(feature_id, _METAMAGIC_NAMES[feature_id], cost)
                )
    return tuple(options)


def apply_metamagic_to_combat_action(
    actor: Actor,
    action: object,
    metamagic_ids: tuple[str, ...] | list[str],
) -> object:
    selected = tuple(dict.fromkeys(str(value) for value in metamagic_ids if str(value)))
    if not selected:
        return action
    if len(selected) > 1 and (
        len(selected) != 2 or "metamagic_empowered" not in selected
    ):
        raise ValueError(
            "Do jednego czaru można użyć tylko jednej opcji Metamagic; "
            "Empowered Spell może być połączone z jedną inną opcją."
        )
    spell = next(
        (candidate for candidate in actor.spells if candidate.id == getattr(action, "id", "")),
        None,
    )
    if spell is None:
        raise ValueError("Metamagic działa wyłącznie na znany czar.")
    for feature_id in selected:
        if not actor_has_feature(actor, feature_id):
            raise ValueError(f"Postać nie zna opcji {_METAMAGIC_NAMES.get(feature_id, feature_id)}.")
        if not _metamagic_is_compatible_with_action(feature_id, action, spell):
            raise ValueError(
                f"Opcja {_METAMAGIC_NAMES.get(feature_id, feature_id)} "
                f"nie działa z czarem {getattr(action, 'name', spell.name)}."
            )
    spell_level = int(getattr(action, "spell_level", 0))
    cost = sum(
        metamagic_sorcery_point_cost(feature_id, spell_level=spell_level)
        for feature_id in selected
    )
    if not can_spend_actor_resource(actor, "sorcery_points", cost):
        raise ValueError(f"Brak {cost} Sorcery Points na wybrane Metamagic.")
    range_feet = int(getattr(action, "range_feet", 0))
    action_cost = getattr(action, "action_cost", ActionEconomyCost.ACTION)
    duration_multiplier = int(getattr(action, "duration_multiplier", 1))
    target_count = int(getattr(action, "target_count", 1))
    if "metamagic_distant" in selected:
        range_feet = (
            30
            if spell.range.kind == SpellRangeKind.TOUCH
            else max(range_feet, spell.range.feet) * 2
        )
    if "metamagic_quickened" in selected:
        action_cost = ActionEconomyCost.BONUS_ACTION
    if "metamagic_extended" in selected:
        duration_multiplier = 2
    if "metamagic_twinned" in selected:
        target_count = 2
    return replace(
        action,
        range_feet=range_feet,
        action_cost=action_cost,
        duration_multiplier=duration_multiplier,
        target_count=target_count,
        resource_pool_id="sorcery_points",
        resource_cost=cost,
        metamagic_ids=selected,
    )


def _is_spell_source(source: AttackSource | HealingSource) -> bool:
    return (
        source.source_type == AttackSourceType.SPELL
        if isinstance(source, AttackSource)
        else source.source_type == HealingSourceType.SPELL
    )


def _metamagic_is_compatible(feature_id: str, source: AttackSource | HealingSource, spell: object) -> bool:
    if feature_id == "metamagic_careful":
        return (
            isinstance(source, AttackSource)
            and source.area is not None
            and bool(source.save_ability)
        )
    if feature_id == "metamagic_distant":
        return spell.range.kind in {SpellRangeKind.TOUCH, SpellRangeKind.DISTANCE}
    if feature_id == "metamagic_empowered":
        return (
            isinstance(source, AttackSource)
            and bool(source.damage_components)
            and any(component.dice is not None for component in source.damage_components)
        )
    if feature_id == "metamagic_extended":
        return spell.duration.kind not in {
            SpellDurationKind.INSTANTANEOUS,
            SpellDurationKind.UNTIL_DISPELLED,
        }
    if feature_id == "metamagic_heightened":
        return isinstance(source, AttackSource) and bool(source.save_ability)
    if feature_id == "metamagic_quickened":
        return source.action_cost == ActionEconomyCost.ACTION
    if feature_id == "metamagic_subtle":
        return bool(spell.components.verbal or spell.components.somatic)
    if feature_id == "metamagic_twinned":
        return (
            source.range_feet > 0
            and spell.range.kind != SpellRangeKind.SELF
            and not (isinstance(source, AttackSource) and source.area is not None)
            and not (
                spell.scaling is not None
                and spell.scaling.targets_per_slot_level > 0
            )
        )
    return False


def _metamagic_is_compatible_with_action(
    feature_id: str,
    action: object,
    spell: object,
) -> bool:
    if feature_id == "metamagic_careful":
        return bool(getattr(action, "save_ability", None))
    if feature_id == "metamagic_distant":
        return spell.range.kind in {SpellRangeKind.TOUCH, SpellRangeKind.DISTANCE}
    if feature_id == "metamagic_empowered":
        return getattr(action, "resolution_mode", "") == "table_assisted"
    if feature_id == "metamagic_extended":
        return spell.duration.kind not in {
            SpellDurationKind.INSTANTANEOUS,
            SpellDurationKind.UNTIL_DISPELLED,
        }
    if feature_id == "metamagic_heightened":
        return bool(getattr(action, "save_ability", None))
    if feature_id == "metamagic_quickened":
        return getattr(action, "action_cost", None) == ActionEconomyCost.ACTION
    if feature_id == "metamagic_subtle":
        return bool(spell.components.verbal or spell.components.somatic)
    if feature_id == "metamagic_twinned":
        return (
            int(getattr(action, "target_count", 1)) == 1
            and getattr(action, "target_faction", "") != "self"
            and spell.range.kind != SpellRangeKind.SELF
            and not (
                spell.scaling is not None
                and spell.scaling.targets_per_slot_level > 0
            )
        )
    return False


def dark_ones_blessing_temporary_hit_points(actor: Actor) -> int:
    _require_feature(actor, "dark_ones_blessing")
    return max(0, actor.level + ability_modifier(actor.ability_scores.charisma))


def apply_agonizing_blast(actor: Actor, source: AttackSource) -> AttackSource:
    if (
        not actor_has_feature(actor, "agonizing_blast")
        or source.id != "eldritch_blast"
    ):
        return source
    bonus = ability_modifier(actor.ability_scores.charisma)
    components = tuple(
        replace(component, modifier=component.modifier + bonus)
        if component.id == "base"
        else component
        for component in source.damage_components
    )
    return replace(
        source,
        damage_modifier=source.damage_modifier + bonus,
        damage_components=components,
        damage_hint=f"{source.damage_hint} + {bonus} (Agonizing Blast)",
    )


def colossus_slayer_damage(
    actor: Actor,
    target: Actor,
    *,
    damage_type: DamageType,
) -> DamageComponentSpec | None:
    if (
        not actor_has_feature(actor, "colossus_slayer")
        or target.hp >= target.max_hp
        or target.is_defeated()
    ):
        return None
    return DamageComponentSpec(
        id="colossus_slayer",
        damage_type=damage_type,
        dice=DiceExpression(1, 8),
        label="Colossus Slayer",
    )


def sculpt_spells_protected_creature_count(actor: Actor) -> int:
    _require_feature(actor, "sculpt_spells")
    return 1 + actor.level


def sacred_weapon_attack_modifier(actor: Actor) -> RollModifier:
    _require_feature(actor, "channel_divinity_sacred_weapon")
    return RollModifier(
        "Sacred Weapon",
        max(1, ability_modifier(actor.ability_scores.charisma)),
        RollModifierType.FEATURE,
        stacking_key="channel_divinity_sacred_weapon",
    )


def _require_feature(actor: Actor, feature_id: str) -> None:
    if not actor_has_feature(actor, feature_id):
        raise ValueError(f"Postać nie posiada cechy {feature_id}.")


__all__ = [
    "apply_agonizing_blast",
    "bardic_inspiration_die_sides",
    "colossus_slayer_damage",
    "dark_ones_blessing_temporary_hit_points",
    "DeflectMissilesResult",
    "deflect_missiles",
    "deflected_missile_attack_source",
    "divine_smite_damage",
    "FontOfMagicConversion",
    "JumpDistances",
    "convert_spell_slot_to_sorcery_points",
    "create_spell_slot_from_sorcery_points",
    "apply_metamagic_to_source",
    "apply_metamagic_to_combat_action",
    "METAMAGIC_FEATURE_IDS",
    "MetamagicOption",
    "metamagic_options_for_source",
    "metamagic_options_for_combat_action",
    "metamagic_sorcery_point_cost",
    "jump_distances",
    "climbing_movement_cost",
    "open_hand_technique_save_dc",
    "natural_recovery_capacity",
    "PreserveLifeAllocation",
    "preserve_life_capacity",
    "sacred_weapon_attack_modifier",
    "sculpt_spells_protected_creature_count",
    "song_of_rest_die_sides",
    "sorcery_point_cost_for_slot",
    "sorcery_points_from_slot",
    "validate_preserve_life_allocations",
    "WildShapeLimits",
    "wild_shape_limits",
]
