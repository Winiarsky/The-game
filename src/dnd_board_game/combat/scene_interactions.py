from __future__ import annotations

from dataclasses import dataclass, replace
from random import Random
from typing import Mapping

from dnd_board_game.actors import (
    Actor,
    Faction,
    actor_has_feature,
    saving_throw_roll_modifiers,
)
from dnd_board_game.core.damage_types import DamageType
from dnd_board_game.rules import (
    ActiveEffect as ActiveCombatEffect,
    D20RollInput,
    D20RollRequest,
    EffectDuration,
    EffectEvent,
    EffectEventType,
    EffectSource,
    EffectSourceType,
    RollMode,
    RollModifier,
    RollModifierType,
    apply_active_effect,
    effect_expiration_label,
    effect_summary_label,
    effect_value_label,
    expire_active_effects,
    resolve_d20_roll,
    resolve_saving_throw,
    ability_modifier,
    DiceExpression,
)
from dnd_board_game.world import Coordinate

from .scene import SceneInteraction, SceneObject, available_scene_interactions, visible_scene_objects
from .action_economy import ActionEconomyCost, action_economy_cost_label
from .attack_flow import AttackSourceType
from .session import ActionUse, CombatState, can_pay_action_economy_cost, replace_actor
from .damage import DamageComponentSpec
from .spells import grid_distance_feet


@dataclass(frozen=True, slots=True)
class CombatInteractionOption:
    id: str
    label: str
    description: str
    object_id: str
    object_name: str
    target_position: Coordinate
    conditions: tuple[str, ...] = ()
    action_cost: ActionEconomyCost = ActionEconomyCost.ACTION

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "object_id": self.object_id,
            "object_name": self.object_name,
            "target_position": [self.target_position.col, self.target_position.row],
            "conditions": list(self.conditions),
            "action_cost": self.action_cost.value,
            "action_cost_label": action_economy_cost_label(self.action_cost),
        }


@dataclass(frozen=True, slots=True)
class MirrorImageOutcome:
    effect_id: str
    redirect_roll: int
    redirect_threshold: int
    redirected: bool
    duplicate_ac: int
    duplicate_hit: bool
    duplicates_before: int
    duplicates_after: int


def resolve_mirror_image_redirect(
    target: Actor,
    *,
    attack_total: int,
    active_effects: tuple[ActiveCombatEffect, ...],
    redirect_roll: int,
) -> MirrorImageOutcome | None:
    effect = next(
        (
            candidate
            for candidate in active_effects
            if candidate.actor_id == str(target.id)
            and candidate.kind == "mirror_image"
            and candidate.value > 0
        ),
        None,
    )
    if effect is None:
        return None
    if not 1 <= redirect_roll <= 20:
        raise ValueError("Mirror Image redirect roll must be between 1 and 20.")
    threshold = {3: 6, 2: 8, 1: 11}.get(effect.value, 6)
    redirected = redirect_roll >= threshold
    duplicate_ac = 10 + ability_modifier(target.ability_scores.dexterity)
    duplicate_hit = redirected and attack_total >= duplicate_ac
    return MirrorImageOutcome(
        effect_id=effect.id,
        redirect_roll=redirect_roll,
        redirect_threshold=threshold,
        redirected=redirected,
        duplicate_ac=duplicate_ac,
        duplicate_hit=duplicate_hit,
        duplicates_before=effect.value,
        duplicates_after=effect.value - 1 if duplicate_hit else effect.value,
    )


def apply_mirror_image_outcome(
    active_effects: tuple[ActiveCombatEffect, ...],
    outcome: MirrorImageOutcome | None,
) -> tuple[ActiveCombatEffect, ...]:
    if outcome is None or not outcome.duplicate_hit:
        return active_effects
    if outcome.duplicates_after <= 0:
        return tuple(
            effect
            for effect in active_effects
            if effect.id != outcome.effect_id
        )
    return tuple(
        replace(effect, value=outcome.duplicates_after)
        if effect.id == outcome.effect_id
        else effect
        for effect in active_effects
    )


@dataclass(frozen=True, slots=True)
class AppliedCombatInteraction:
    state: CombatState
    active_effects: tuple[ActiveCombatEffect, ...]
    message: str
    saving_throw: CombatInteractionSavingThrow | None = None


@dataclass(frozen=True, slots=True)
class CombatInteractionSavingThrow:
    actor_id: str
    actor_name: str
    ability: str
    dc: int
    natural_roll: int
    modifier: int
    total: int
    success: bool
    modifiers: tuple[RollModifier, ...] = ()

    def as_payload(self) -> dict[str, object]:
        return {
            "actor_id": self.actor_id,
            "actor_name": self.actor_name,
            "ability": self.ability,
            "dc": self.dc,
            "natural_roll": self.natural_roll,
            "modifier": self.modifier,
            "total": self.total,
            "success": self.success,
            "modifier_components": [
                {
                    "label": modifier.label,
                    "value": modifier.value,
                    "modifier_type": modifier.modifier_type.value,
                }
                for modifier in self.modifiers
            ],
        }


def available_combat_interaction_options(
    scene_objects: tuple[SceneObject, ...],
    state: CombatState,
    actor: Actor,
    position: Coordinate,
) -> tuple[CombatInteractionOption, ...]:
    if actor.faction != Faction.ALLY:
        return ()
    scene_object = scene_object_at_position(scene_objects, position)
    if scene_object is None:
        return ()
    options: list[CombatInteractionOption] = []
    for interaction in available_scene_interactions(scene_object):
        if not interaction_conditions_met(interaction, scene_object, state, actor, position):
            continue
        action_cost = _interaction_action_cost(
            state,
            actor,
            interaction.action_cost,
        )
        if action_cost is None:
            continue
        adjacent_target = (
            adjacent_living_enemy(state, actor)
            if any(condition.condition_type == "adjacent_enemy_exists" for condition in interaction.conditions)
            else None
        )
        description = interaction.description
        if adjacent_target is not None:
            description += (
                f" Aktualny cel: {adjacent_target.name} na polu "
                f"{adjacent_target.position.as_tuple()}; sąsiednie pole obejmuje także skos."
            )
        options.append(
            CombatInteractionOption(
                id=interaction.id,
                label=interaction.label,
                description=description,
                object_id=scene_object.id,
                object_name=scene_object.name,
                target_position=position,
                conditions=tuple(condition_label(condition.condition_type) for condition in interaction.conditions),
                action_cost=action_cost,
            )
        )
    return tuple(options)


def _interaction_action_cost(
    state: CombatState,
    actor: Actor,
    authored_cost: ActionEconomyCost,
) -> ActionEconomyCost | None:
    if (
        actor_has_feature(actor, "fast_hands")
        and state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE
        and authored_cost == ActionEconomyCost.ACTION
    ):
        return ActionEconomyCost.BONUS_ACTION
    if can_pay_action_economy_cost(state, authored_cost):
        return authored_cost
    if (
        actor_has_feature(actor, "fast_hands")
        and state.turn_action.bonus_action_use == ActionUse.ACTION_AVAILABLE
        and authored_cost == ActionEconomyCost.OBJECT_INTERACTION
    ):
        return ActionEconomyCost.BONUS_ACTION
    return None


def combat_interaction_positions(
    scene_objects: tuple[SceneObject, ...],
    state: CombatState,
    actor: Actor,
) -> tuple[Coordinate, ...]:
    positions = {
        position
        for scene_object in visible_scene_objects(scene_objects)
        for position in scene_object.positions
        if available_combat_interaction_options(scene_objects, state, actor, position)
    }
    return tuple(sorted(positions))


def combat_interaction_hint_positions(
    scene_objects: tuple[SceneObject, ...],
    state: CombatState,
    actor: Actor,
    reachable_tiles: frozenset[Coordinate] = frozenset(),
) -> tuple[Coordinate, ...]:
    if actor.faction != Faction.ALLY:
        return ()
    candidate_actor_positions = frozenset((*reachable_tiles, actor.position))
    positions: set[Coordinate] = set()
    for scene_object in visible_scene_objects(scene_objects):
        if not available_scene_interactions(scene_object):
            continue
        for position in scene_object.positions:
            for candidate in candidate_actor_positions:
                moved_actor = replace(actor, position=candidate)
                moved_state = replace_actor(state, moved_actor)
                if available_combat_interaction_options(scene_objects, moved_state, moved_actor, position):
                    positions.add(position)
                    break
    return tuple(sorted(positions))


def interaction_conditions_met(
    interaction: SceneInteraction,
    scene_object: SceneObject,
    state: CombatState,
    actor: Actor,
    target_position: Coordinate,
) -> bool:
    conditions = interaction.conditions or ()
    if not conditions:
        return any(coordinates_adjacent_or_same(actor.position, object_position) for object_position in scene_object.positions)
    for condition in conditions:
        condition_type = condition.condition_type
        if condition_type == "action_available" and state.turn_action.action_use != ActionUse.ACTION_AVAILABLE:
            return False
        if condition_type == "actor_adjacent_to_object" and not any(
            coordinates_adjacent_or_same(actor.position, object_position) for object_position in scene_object.positions
        ):
            return False
        if condition_type == "actor_on_object" and actor.position not in scene_object.positions:
            return False
        if condition_type == "adjacent_enemy_exists" and adjacent_living_enemy(state, actor) is None:
            return False
        if condition_type == "target_tile_free" and living_actor_at_position(state, target_position, exclude_actor_id=str(actor.id)) is not None:
            return False
    return True


def apply_combat_interaction_effects(
    *,
    state: CombatState,
    actor: Actor,
    scene_object: SceneObject,
    interaction: SceneInteraction,
    target_position: Coordinate,
    active_effects: tuple[ActiveCombatEffect, ...],
    saving_throw_rolls: Mapping[str, int] | None = None,
    rng: Random | None = None,
) -> AppliedCombatInteraction:
    updated_state = state
    updated_effects = active_effects
    messages: list[str] = []
    saving_throw: CombatInteractionSavingThrow | None = None
    for effect in interaction.effects:
        params = effect_parameters(effect.parameters)
        if effect.effect_type == "grant_ac_bonus_until_move":
            value = int(params.get("value", scene_object.cover_bonus or 0))
            label = str(params.get("label", f"Osłona: {scene_object.name}"))
            updated_state, updated_effects = remove_combat_effects_from_state(
                updated_state,
                updated_effects,
                str(actor.id),
                kind="grant_ac_bonus_until_move",
            )
            current_actor = actor_by_id(updated_state, str(actor.id))
            updated_state = replace_actor(updated_state, replace(current_actor, ac=current_actor.ac + value))
            updated_effects = replace_effect(
                updated_effects,
                str(actor.id),
                kind="grant_ac_bonus_until_move",
                new_effect=ActiveCombatEffect(
                    id=f"grant_ac_bonus_until_move:{actor.id}:{scene_object.id}",
                    actor_id=str(actor.id),
                    kind="grant_ac_bonus_until_move",
                    label=label,
                    object_id=scene_object.id,
                    value=value,
                    anchor_position=current_actor.position,
                    base_ac=current_actor.ac,
                    source=EffectSource(
                        EffectSourceType.SCENE,
                        scene_object.id,
                        scene_object.name,
                    ),
                    duration=EffectDuration.WHILE_AT_POSITION,
                ),
            )
            messages.append(f"{label}: AC +{value} do opuszczenia pola.")
        elif effect.effect_type == "move_actor_to_tile":
            if living_actor_at_position(updated_state, target_position, exclude_actor_id=str(actor.id)) is not None:
                raise ValueError("Pole docelowe jest zajęte.")
            updated_state, updated_effects = remove_combat_effects_from_state(updated_state, updated_effects, str(actor.id))
            current_actor = actor_by_id(updated_state, str(actor.id))
            updated_state = replace_actor(updated_state, replace(current_actor, position=target_position))
            messages.append(f"{actor.name} przemieszcza się na pole {target_position.as_tuple()}.")
        elif effect.effect_type == "grant_attack_bonus_while_on_object":
            value = int(params.get("value", 0))
            label = str(params.get("label", f"Pozycja: {scene_object.name}"))
            updated_effects = replace_effect(
                updated_effects,
                str(actor.id),
                kind="grant_attack_bonus_while_on_object",
                new_effect=ActiveCombatEffect(
                    id=f"grant_attack_bonus_while_on_object:{actor.id}:{scene_object.id}",
                    actor_id=str(actor.id),
                    kind="grant_attack_bonus_while_on_object",
                    label=label,
                    object_id=scene_object.id,
                    value=value,
                    anchor_position=target_position,
                    source=EffectSource(
                        EffectSourceType.SCENE,
                        scene_object.id,
                        scene_object.name,
                    ),
                    duration=EffectDuration.WHILE_AT_POSITION,
                ),
            )
            messages.append(f"{label}: ataki +{value}, dopóki aktor stoi na obiekcie.")
        elif effect.effect_type == "grant_next_attack_penalty":
            value = int(params.get("value", 0))
            label = str(params.get("label", f"Utrudnienie: {scene_object.name}"))
            target = adjacent_living_enemy(updated_state, actor)
            if target is None:
                raise ValueError("Brak sąsiedniego przeciwnika dla tej interakcji.")
            save_dc = params.get("saving_throw_dc")
            if save_dc is not None:
                ability = str(params.get("saving_throw_ability", "dexterity"))
                dc = int(save_dc)
                natural_roll = saving_throw_natural_roll(target, saving_throw_rolls, rng)
                from .auras import saving_throw_aura_modifiers

                request = D20RollRequest(
                    modifiers=(
                        *saving_throw_roll_modifiers(target, ability),
                        *saving_throw_aura_modifiers(updated_state.actors, target),
                    )
                )
                roll = resolve_d20_roll(D20RollInput(request, natural_roll))
                check = resolve_saving_throw(roll, dc)
                saving_throw = CombatInteractionSavingThrow(
                    actor_id=str(target.id),
                    actor_name=target.name,
                    ability=ability,
                    dc=dc,
                    natural_roll=roll.natural_roll,
                    modifier=roll.breakdown.modifier_total,
                    total=roll.total,
                    success=check.success,
                    modifiers=roll.breakdown.active_modifiers,
                )
                roll_message = (
                    f"{target.name} wykonuje rzut obronny na {_ability_label_pl(ability)}: "
                    f"d20 {roll.natural_roll}, modyfikator {format_signed(roll.breakdown.modifier_total)}, "
                    f"razem {roll.total} przeciw ST {dc}."
                )
                if check.success:
                    messages.append(f"{roll_message} Sukces: gruz nie nakłada kary.")
                    continue
                messages.append(f"{roll_message} Porażka: {label} działa.")
            updated_effects = replace_effect(
                updated_effects,
                str(target.id),
                kind="grant_next_attack_penalty",
                new_effect=ActiveCombatEffect(
                    id=f"grant_next_attack_penalty:{target.id}:{scene_object.id}",
                    actor_id=str(target.id),
                    kind="grant_next_attack_penalty",
                    label=label,
                    object_id=scene_object.id,
                    value=value,
                    anchor_position=actor.position,
                    source=EffectSource(
                        EffectSourceType.SCENE,
                        scene_object.id,
                        scene_object.name,
                    ),
                    duration=EffectDuration.UNTIL_NEXT_ATTACK,
                ),
            )
            messages.append(f"{label}: {target.name} ma {value} do następnego ataku.")
        else:
            raise ValueError(f"Nieznany efekt interakcji walki: {effect.effect_type}.")
    return AppliedCombatInteraction(
        state=updated_state,
        active_effects=updated_effects,
        message=" ".join(messages) or f"Interakcja zakończona: {interaction.label}.",
        saving_throw=saving_throw,
    )


def expire_invalid_combat_effects(
    state: CombatState,
    scene_objects: tuple[SceneObject, ...],
    active_effects: tuple[ActiveCombatEffect, ...],
) -> tuple[CombatState, tuple[ActiveCombatEffect, ...]]:
    updated_state = state
    kept: list[ActiveCombatEffect] = []
    for effect in active_effects:
        actor = maybe_actor_by_id(updated_state, effect.actor_id)
        valid = actor is not None and not actor.is_defeated()
        if valid and effect.kind == "grant_ac_bonus_until_move":
            valid = not expire_active_effects(
                (effect,),
                EffectEvent(
                    EffectEventType.ACTOR_MOVED,
                    actor_id=str(actor.id),
                    position=actor.position,
                ),
            ).expired_effects
        elif valid and effect.kind == "grant_attack_bonus_while_on_object":
            scene_object = scene_object_by_id(scene_objects, effect.object_id)
            valid = scene_object is not None and actor.position in scene_object.positions
        elif valid and effect.kind == "grant_next_attack_penalty":
            valid = True
        if valid:
            kept.append(effect)
        else:
            updated_state = restore_effect_on_state(updated_state, effect)
    return updated_state, tuple(kept)


def expire_combat_effects(
    state: CombatState,
    active_effects: tuple[ActiveCombatEffect, ...],
    event: EffectEvent,
) -> tuple[CombatState, tuple[ActiveCombatEffect, ...], tuple[ActiveCombatEffect, ...]]:
    """Expire effects for an event and undo any materialized actor-state changes."""

    expiration = expire_active_effects(active_effects, event)
    updated_state = state
    for effect in expiration.expired_effects:
        updated_state = restore_effect_on_state(updated_state, effect)
    return updated_state, expiration.active_effects, expiration.expired_effects


def attack_source_with_combat_effects(actor: Actor, source, active_effects: tuple[ActiveCombatEffect, ...]):
    modifiers = []
    flame_blade = next(
        (
            effect
            for effect in active_effects
            if effect.actor_id == str(actor.id)
            and effect.kind == "flame_blade"
            and getattr(getattr(source, "attack_kind", None), "value", "")
            == "melee"
        ),
        None,
    )
    if flame_blade is not None:
        from dnd_board_game.rules import spellcasting_ability_for_spell

        source = replace(
            source,
            id="flame_blade",
            name="Ostrze płomieni",
            source_type=AttackSourceType.SPELL,
            ability=spellcasting_ability_for_spell(actor, "flame_blade")
            or "wisdom",
            damage_modifier=0,
            damage_components=(
                DamageComponentSpec(
                    id="flame_blade",
                    damage_type=DamageType.FIRE,
                    dice=DiceExpression(max(3, flame_blade.value), 6),
                    label="Ostrze płomieni",
                ),
            ),
            damage_hint=f"{max(3, flame_blade.value)}k6 fire",
        )
    shillelagh = any(
        effect.actor_id == str(actor.id) and effect.kind == "shillelagh"
        for effect in active_effects
    ) and (
        getattr(source, "proficiency_id", "") in {"club", "quarterstaff"}
        or getattr(source, "id", "") in {"club", "quarterstaff"}
        or getattr(source, "source_item_id", "") in {"club", "quarterstaff"}
    )
    shillelagh_modifier_difference = 0
    enfeebled = any(
        effect.actor_id == str(actor.id)
        and effect.kind == "ray_of_enfeeblement"
        for effect in active_effects
    ) and (
        getattr(getattr(source, "source_type", None), "value", "") == "weapon"
        and getattr(source, "ability", None) == "strength"
    )
    if enfeebled:
        source = replace(source, damage_divisor=2)
    if shillelagh:
        from dnd_board_game.rules import ability_modifier

        casting_modifier = actor.spell_save_dc - 8 - actor.proficiency_bonus
        current_modifier = ability_modifier(
            getattr(actor.ability_scores, getattr(source, "ability", "strength"))
        )
        shillelagh_modifier_difference = casting_modifier - current_modifier
        if shillelagh_modifier_difference:
            modifiers.append(
                RollModifier(
                    "Shillelagh",
                    shillelagh_modifier_difference,
                    RollModifierType.SPELL,
                    stacking_key="shillelagh",
                )
            )
    for effect in active_effects:
        if effect.actor_id != str(actor.id):
            continue
        if effect.kind not in {
            "grant_attack_bonus_while_on_object",
            "grant_next_attack_penalty",
            "strength_potion",
            "concentration_attack_bonus",
            "sacred_weapon_attack_bonus",
            "magic_weapon",
        }:
            continue
        if effect.kind == "strength_potion" and getattr(source, "ability", None) != "strength":
            continue
        if (
            effect.kind == "sacred_weapon_attack_bonus"
            and effect.object_id != f"weapon:{getattr(source, 'source_item_id', '')}"
        ):
            continue
        if (
            effect.kind == "magic_weapon"
            and effect.object_id != f"weapon:{getattr(source, 'source_item_id', '')}"
        ):
            continue
        modifiers.append(
            RollModifier(
                effect.label,
                effect.value,
                RollModifierType.CUSTOM,
                stacking_key=effect.id,
            )
        )
    damage_bonus = sum(
        effect.value
        for effect in active_effects
        if effect.actor_id == str(actor.id)
        and (
            (
                effect.kind == "strength_potion"
                and getattr(source, "ability", None) == "strength"
            )
            or (
                effect.kind == "rage"
                and getattr(source, "ability", None) == "strength"
                and getattr(getattr(source, "attack_kind", None), "value", "") == "melee"
            )
            or (
                effect.kind == "magic_weapon"
                and getattr(getattr(source, "source_type", None), "value", "") == "weapon"
                and effect.object_id
                == f"weapon:{getattr(source, 'source_item_id', '')}"
            )
        )
    )
    if shillelagh:
        damage_bonus += shillelagh_modifier_difference
        components = list(source.damage_components)
        if components and components[0].dice is not None:
            components[0] = replace(
                components[0],
                dice=DiceExpression(components[0].dice.count, 8),
            )
            source = replace(
                source,
                ability="wisdom",
                damage_components=tuple(components),
                damage_hint=" + ".join(
                    component.hint() for component in components
                ),
            )
    reckless = any(
        effect.actor_id == str(actor.id)
        and effect.kind == "reckless_attack"
        and getattr(source, "ability", None) == "strength"
        and getattr(getattr(source, "attack_kind", None), "value", "") == "melee"
        for effect in active_effects
    )
    next_attack_advantage = any(
        effect.actor_id == str(actor.id)
        and effect.kind == "next_attack_advantage"
        and effect.target_actor_id is None
        for effect in active_effects
    )
    vicious_mockery_disadvantage = any(
        effect.actor_id == str(actor.id)
        and effect.kind == "vicious_mockery_disadvantage"
        and getattr(getattr(source, "source_type", None), "value", "") == "weapon"
        for effect in active_effects
    )
    heat_metal_disadvantage = any(
        effect.actor_id == str(actor.id)
        and effect.kind == "heat_metal_disadvantage"
        for effect in active_effects
    )
    extra_components: list[DamageComponentSpec] = []
    if getattr(getattr(source, "source_type", None), "value", "") == "weapon":
        for effect in active_effects:
            if (
                effect.actor_id == str(actor.id)
                and effect.kind == "divine_favor_damage"
            ):
                extra_components.append(
                    DamageComponentSpec(
                        id="divine_favor",
                        damage_type=DamageType.RADIANT,
                        dice=DiceExpression(1, 4),
                        label="Divine Favor",
                    )
                )
            if (
                effect.actor_id == str(actor.id)
                and effect.kind == "enlarge_reduce:enlarge"
            ):
                extra_components.append(
                    DamageComponentSpec(
                        id="enlarge",
                        damage_type=source.damage_components[0].damage_type,
                        dice=DiceExpression(1, 4),
                        label="Enlarge",
                    )
                )
            if (
                effect.actor_id == str(actor.id)
                and effect.kind == "branding_smite"
            ):
                dice_count = max(2, effect.value)
                extra_components.append(
                    DamageComponentSpec(
                        id="branding_smite",
                        damage_type=DamageType.RADIANT,
                        dice=DiceExpression(dice_count, 6),
                        label="Piętnujące porażenie",
                    )
                )
    existing_component_ids = {
        component.id for component in source.damage_components
    }
    extra_components = [
        component
        for component in extra_components
        if component.id not in existing_component_ids
    ]
    if (
        not modifiers
        and damage_bonus == 0
        and not reckless
        and not next_attack_advantage
        and not vicious_mockery_disadvantage
        and not extra_components
        and not heat_metal_disadvantage
    ):
        return source
    mode = source.attack_roll_request.mode
    if reckless or next_attack_advantage:
        mode = _with_advantage(mode)
    if vicious_mockery_disadvantage or heat_metal_disadvantage:
        mode = _with_disadvantage(mode)
    return replace(
        source,
        attack_roll_request=D20RollRequest(
            mode=mode,
            modifiers=source.attack_roll_request.modifiers + tuple(modifiers),
        ),
        damage_modifier=source.damage_modifier + damage_bonus,
        damage_components=(*source.damage_components, *extra_components),
        damage_hint=(
            " + ".join(
                (
                    _damage_hint_with_bonus(source, damage_bonus)
                    if damage_bonus
                    else source.damage_hint,
                    *(component.hint() for component in extra_components),
                )
            )
        ),
    )


def attack_source_with_target_combat_effects(
    attacker: Actor,
    target: Actor,
    source,
    active_effects: tuple[ActiveCombatEffect, ...],
):
    source = attack_source_with_combat_effects(attacker, source, active_effects)
    modifiers = []
    mode = source.attack_roll_request.mode
    if any(
        effect.actor_id == str(attacker.id)
        and effect.kind == "next_attack_advantage"
        and effect.target_actor_id == str(target.id)
        for effect in active_effects
    ):
        mode = _with_advantage(mode)
    obscuring_zones = tuple(
        effect
        for effect in active_effects
        if effect.kind == "obscuring_zone"
        and effect.anchor_position is not None
    )
    for zone in obscuring_zones:
        if grid_distance_feet(attacker.position, zone.anchor_position) <= zone.value:
            mode = _with_disadvantage(mode)
        if grid_distance_feet(target.position, zone.anchor_position) <= zone.value:
            mode = _with_advantage(mode)
    if getattr(source, "advantage_against_metal_armor", False) and _wears_metal_armor(target):
        mode = _with_advantage(mode)
    attacker_sees_invisible = any(
        effect.actor_id == str(attacker.id)
        and effect.kind == "see_invisibility"
        for effect in active_effects
    )
    target_sees_invisible = any(
        effect.actor_id == str(target.id)
        and effect.kind == "see_invisibility"
        for effect in active_effects
    )
    protected_from_attacker = any(
        effect.actor_id == str(target.id)
        and effect.kind == "protection_from_evil_and_good"
        and attacker.creature_type
        in {"aberration", "celestial", "elemental", "fey", "fiend", "undead"}
        for effect in active_effects
    )
    if protected_from_attacker:
        mode = _with_disadvantage(mode)
    for effect in active_effects:
        ignores_blur = (
            effect.object_id in {"spell:blur", "combat_action:blur"}
            and max(
                attacker.senses.blindsight_feet,
                attacker.senses.truesight_feet,
            )
            >= grid_distance_feet(attacker.position, target.position)
        )
        if (
            effect.actor_id == str(target.id)
            and effect.kind
            in {"dodge_until_next_turn", "attacks_against_disadvantage"}
            and not ignores_blur
        ):
            mode = _with_disadvantage(mode)
        if (
            effect.actor_id == str(target.id)
            and effect.kind == "invisibility"
            and not attacker_sees_invisible
        ):
            mode = _with_disadvantage(mode)
        if effect.actor_id == str(target.id) and effect.kind in {
            "attacks_against_advantage",
            "guiding_bolt_mark",
        }:
            mode = _with_advantage(mode)
        if (
            effect.actor_id == str(attacker.id)
            and effect.kind == "invisibility"
            and not target_sees_invisible
        ):
            mode = _with_advantage(mode)
        if (
            effect.kind == "help_attack_advantage"
            and effect.actor_id == str(attacker.id)
            and effect.target_actor_id == str(target.id)
        ):
            mode = _with_advantage(mode)
        if effect.actor_id == str(target.id) and effect.kind == "reckless_attack":
            mode = _with_advantage(mode)
        if (
            effect.actor_id == str(target.id)
            and effect.kind == "hunters_mark"
            and effect.source_actor_id == str(attacker.id)
            and getattr(getattr(source, "source_type", None), "value", "") == "weapon"
            and source.damage_components
            and all(
                component.id != "hunters_mark"
                for component in source.damage_components
            )
        ):
            component = DamageComponentSpec(
                id="hunters_mark",
                damage_type=source.damage_components[0].damage_type,
                dice=DiceExpression(1, 6),
                label="Znak łowcy",
            )
            source = replace(
                source,
                damage_components=(*source.damage_components, component),
                damage_hint=f"{source.damage_hint} + {component.hint()}",
            )
    if target.is_unconscious():
        mode = _with_advantage(mode)
    if not modifiers and mode == source.attack_roll_request.mode:
        return source
    return replace(
        source,
        attack_roll_request=D20RollRequest(
            mode=mode,
            modifiers=source.attack_roll_request.modifiers + tuple(modifiers),
        ),
    )


def _wears_metal_armor(actor: Actor) -> bool:
    metal_armor_ids = {
        "chain_shirt",
        "scale_mail",
        "breastplate",
        "half_plate",
        "ring_mail",
        "chain_mail",
        "splint_armor",
        "plate_armor",
    }
    return any(
        item.equipped
        and item.available
        and (item.source_ref or item.id) in metal_armor_ids
        for item in getattr(actor, "inventory", ())
    )


def consume_next_attack_effects(
    active_effects: tuple[ActiveCombatEffect, ...],
    actor_id: str,
    target_actor_id: str | None = None,
) -> tuple[ActiveCombatEffect, ...]:
    remaining = expire_active_effects(
        active_effects,
        EffectEvent(
            EffectEventType.ATTACK_RESOLVED,
            actor_id=actor_id,
            target_actor_id=target_actor_id,
        ),
    ).active_effects
    return tuple(
        effect
        for effect in end_invisibility_effects(remaining, actor_id)
        if not (effect.actor_id == actor_id and effect.kind == "sanctuary")
    )


def end_invisibility_effects(
    active_effects: tuple[ActiveCombatEffect, ...],
    actor_id: str,
) -> tuple[ActiveCombatEffect, ...]:
    """End every invisibility effect carried by an actor after attack or cast."""

    return tuple(
        effect
        for effect in active_effects
        if not (effect.actor_id == actor_id and effect.kind == "invisibility")
    )


def end_sanctuary_effects(
    active_effects: tuple[ActiveCombatEffect, ...],
    actor_id: str,
) -> tuple[ActiveCombatEffect, ...]:
    return tuple(
        effect
        for effect in active_effects
        if not (effect.actor_id == actor_id and effect.kind == "sanctuary")
    )


def expire_turn_start_effects(active_effects: tuple[ActiveCombatEffect, ...], actor_id: str) -> tuple[ActiveCombatEffect, ...]:
    return expire_active_effects(
        active_effects,
        EffectEvent(EffectEventType.TURN_START, actor_id=actor_id),
    ).active_effects


def expire_turn_end_effects(active_effects: tuple[ActiveCombatEffect, ...], actor_id: str) -> tuple[ActiveCombatEffect, ...]:
    return expire_active_effects(
        active_effects,
        EffectEvent(EffectEventType.TURN_END, actor_id=actor_id),
    ).active_effects


def _with_advantage(mode: RollMode) -> RollMode:
    if mode == RollMode.DISADVANTAGE:
        return RollMode.NORMAL
    return RollMode.ADVANTAGE


def _with_disadvantage(mode: RollMode) -> RollMode:
    if mode == RollMode.ADVANTAGE:
        return RollMode.NORMAL
    return RollMode.DISADVANTAGE


def _damage_hint_with_bonus(source, bonus: int) -> str:
    if bonus == 0:
        return source.damage_hint
    if source.damage_die_sides is None:
        total = max(0, int(source.damage_fixed or 0) + int(source.damage_modifier or 0) + bonus)
        return str(total)
    modifier = int(source.damage_modifier or 0) + bonus
    if modifier == 0:
        return f"1d{source.damage_die_sides} {source.damage_type}"
    sign = "+" if modifier > 0 else "-"
    return f"1d{source.damage_die_sides} {sign} {abs(modifier)} {source.damage_type}"


def remove_combat_effects_from_state(
    state: CombatState,
    active_effects: tuple[ActiveCombatEffect, ...],
    actor_id: str,
    *,
    kind: str | None = None,
) -> tuple[CombatState, tuple[ActiveCombatEffect, ...]]:
    remaining: list[ActiveCombatEffect] = []
    updated_state = state
    for effect in active_effects:
        should_remove = effect.actor_id == actor_id and (kind is None or effect.kind == kind)
        if should_remove:
            updated_state = restore_effect_on_state(updated_state, effect)
        else:
            remaining.append(effect)
    return updated_state, tuple(remaining)


def replace_effect(
    active_effects: tuple[ActiveCombatEffect, ...],
    actor_id: str,
    *,
    kind: str,
    new_effect: ActiveCombatEffect,
) -> tuple[ActiveCombatEffect, ...]:
    if new_effect.actor_id != actor_id or new_effect.kind != kind:
        raise ValueError("Replacement effect does not match actor_id and kind.")
    return apply_active_effect(active_effects, new_effect).active_effects


def restore_effect_on_state(state: CombatState, effect: ActiveCombatEffect) -> CombatState:
    actor = maybe_actor_by_id(state, effect.actor_id)
    if actor is None:
        return state
    if effect.kind == "grant_ac_bonus_until_move" and effect.base_ac is not None:
        return replace_actor(state, replace(actor, ac=effect.base_ac))
    if effect.kind == "max_hit_points_bonus":
        maximum = max(1, actor.max_hp - effect.value)
        return replace_actor(
            state,
            replace(actor, max_hp=maximum, hp=min(actor.hp, maximum)),
        )
    if effect.kind == "temporary_hit_points" and actor.temp_hp <= effect.value:
        return replace_actor(state, replace(actor, temp_hp=0))
    return state


def scene_object_at_position(scene_objects: tuple[SceneObject, ...], position: Coordinate) -> SceneObject | None:
    return next((scene_object for scene_object in visible_scene_objects(scene_objects) if position in scene_object.positions), None)


def scene_object_by_id(scene_objects: tuple[SceneObject, ...], object_id: str) -> SceneObject | None:
    return next((scene_object for scene_object in scene_objects if scene_object.id == object_id), None)


def living_actor_at_position(state: CombatState, position: Coordinate, *, exclude_actor_id: str = "") -> Actor | None:
    return next(
        (
            candidate
            for candidate in state.actors
            if str(candidate.id) != exclude_actor_id and not candidate.is_defeated() and candidate.position == position
        ),
        None,
    )


def adjacent_living_enemy(state: CombatState, actor: Actor) -> Actor | None:
    enemies = [
        candidate
        for candidate in state.actors
        if candidate.faction != actor.faction
        and candidate.faction != Faction.NEUTRAL
        and not candidate.is_defeated()
        and coordinates_adjacent_or_same(actor.position, candidate.position)
    ]
    return next(iter(sorted(enemies, key=lambda candidate: (candidate.position.col, candidate.position.row, str(candidate.id)))), None)


def saving_throw_natural_roll(actor: Actor, saving_throw_rolls: Mapping[str, int] | None, rng: Random | None) -> int:
    if saving_throw_rolls is not None and str(actor.id) in saving_throw_rolls:
        return int(saving_throw_rolls[str(actor.id)])
    if rng is not None:
        return rng.randint(1, 20)
    raise ValueError("Brak wyniku rzutu obronnego przeciwnika dla interakcji.")


def format_signed(value: int) -> str:
    return f"+{value}" if value >= 0 else str(value)


def _ability_label_pl(ability: str) -> str:
    return {
        "strength": "Siłę",
        "dexterity": "Zręczność",
        "constitution": "Kondycję",
        "intelligence": "Inteligencję",
        "wisdom": "Mądrość",
        "charisma": "Charyzmę",
    }.get(ability, ability)


def actor_by_id(state: CombatState, actor_id: str) -> Actor:
    actor = maybe_actor_by_id(state, actor_id)
    if actor is None:
        raise ValueError(f"Nieznany aktor walki: {actor_id}.")
    return actor


def maybe_actor_by_id(state: CombatState, actor_id: str) -> Actor | None:
    return next((candidate for candidate in state.actors if str(candidate.id) == actor_id), None)


def coordinates_adjacent_or_same(a: Coordinate, b: Coordinate) -> bool:
    return max(abs(a.col - b.col), abs(a.row - b.row)) <= 1


def effect_parameters(parameters: tuple[tuple[str, object], ...]) -> dict[str, object]:
    return {key: value for key, value in parameters}


def condition_label(condition_type: str) -> str:
    return {
        "action_available": "akcja główna jest dostępna",
        "actor_adjacent_to_object": "aktor stoi przy obiekcie albo na nim",
        "actor_on_object": "aktor stoi na obiekcie",
        "adjacent_enemy_exists": "sąsiedni przeciwnik istnieje",
        "target_tile_free": "pole docelowe jest wolne",
    }.get(condition_type, condition_type)
