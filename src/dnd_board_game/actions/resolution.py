from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Mapping

from dnd_board_game.actors import Actor, spend_actor_resource
from dnd_board_game.combat import (
    ActionEconomyCost,
    AppliedDamageResult,
    AppliedHealingResult,
    AttackSource,
    CombatState,
    CombatCondition,
    DamageComponentInput,
    DamageType,
    HealingSource,
    SpellSaveResult,
    apply_damage_result,
    apply_healing_result,
    apply_save_damage_amount,
    consume_spell_resource,
    has_condition,
    replace_actor,
    resolve_damage,
    resolve_spell_save,
    use_action_economy_cost,
)
from dnd_board_game.rules import RollModifier


@dataclass(frozen=True, slots=True)
class ActionResourceResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    spell_level: int
    spell_resource_consumed: bool
    actor_resource_id: str | None = None
    actor_resource_cost: int = 0


@dataclass(frozen=True, slots=True)
class SingleTargetDamageResolution:
    state: CombatState
    target_id: str
    base_damage: int
    applied_damage: AppliedDamageResult
    saving_throw: SpellSaveResult | None = None


@dataclass(frozen=True, slots=True)
class SingleTargetSaveSpellConfirmation:
    state: CombatState
    resource_use: ActionResourceResolution
    saving_throw: SpellSaveResult


@dataclass(frozen=True, slots=True)
class AreaSpellConfirmation:
    state: CombatState
    resource_use: ActionResourceResolution
    saving_throws: tuple[SpellSaveResult, ...]


@dataclass(frozen=True, slots=True)
class AreaSpellTargetDamage:
    target_id: str
    applied_damage: AppliedDamageResult
    saving_throw: SpellSaveResult | None = None


@dataclass(frozen=True, slots=True)
class AreaSpellDamageResolution:
    state: CombatState
    source: AttackSource
    base_damage: int
    targets: tuple[AreaSpellTargetDamage, ...]


@dataclass(frozen=True, slots=True)
class HealingActionResolution:
    state: CombatState
    resource_use: ActionResourceResolution
    applied_healing: AppliedHealingResult


class ActionResourceResolver:
    def consume_action_and_source_resource(
        self,
        state: CombatState,
        actor: Actor,
        *,
        spell_level: int = 0,
        spell_id: str | None = None,
        cast_level: int | None = None,
        action_cost: ActionEconomyCost = ActionEconomyCost.ACTION,
        resource_pool_id: str | None = None,
        resource_cost: int = 1,
    ) -> ActionResourceResolution:
        action_result = use_action_economy_cost(state, action_cost)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        state_after_action = action_result.state
        actor_after_action = _actor_by_id(state_after_action, str(actor.id))
        resource_result = consume_spell_resource(
            actor_after_action,
            int(spell_level),
            cast_level=cast_level,
            spell_id=spell_id,
        )
        state_after_resource = state_after_action
        if resource_result.actor_after != actor_after_action:
            state_after_resource = replace_actor(state_after_action, resource_result.actor_after)
        actor_after_resource = resource_result.actor_after
        if resource_pool_id is not None:
            usage = spend_actor_resource(
                actor_after_resource,
                resource_pool_id,
                resource_cost,
            )
            actor_after_resource = usage.actor_after
            state_after_resource = replace_actor(state_after_resource, actor_after_resource)
        return ActionResourceResolution(
            state=state_after_resource,
            actor_before=actor,
            actor_after=actor_after_resource,
            spell_level=resource_result.spell_level,
            spell_resource_consumed=resource_result.consumed,
            actor_resource_id=resource_pool_id,
            actor_resource_cost=resource_cost if resource_pool_id is not None else 0,
        )


class AttackActionResolver(ActionResourceResolver):
    def apply_target_damage(
        self,
        state: CombatState,
        *,
        target_id: str,
        source: AttackSource,
        base_damage: int,
        damage_components: tuple[DamageComponentInput, ...] | None = None,
        saving_throw: SpellSaveResult | None = None,
        critical: bool = False,
    ) -> SingleTargetDamageResolution:
        target = _actor_by_id(state, target_id)
        raw_components = damage_components or (
            DamageComponentInput(
                max(0, int(base_damage)),
                DamageType(source.damage_type),
                source.name,
            ),
        )
        adjusted_components = tuple(
            DamageComponentInput(
                apply_save_damage_amount(component.amount, saving_throw),
                component.damage_type,
                component.label,
            )
            for component in raw_components
        )
        damage = resolve_damage(adjusted_components)
        applied = apply_damage_result(target, damage, critical=critical)
        return SingleTargetDamageResolution(
            state=replace_actor(state, applied.actor_after),
            target_id=target_id,
            base_damage=sum(component.amount for component in raw_components),
            applied_damage=applied,
            saving_throw=saving_throw,
        )


class SpellSaveAttackResolver(AttackActionResolver):
    def confirm_target_save_spell(
        self,
        state: CombatState,
        *,
        caster: Actor,
        target: Actor,
        source: AttackSource,
        rng: random.Random,
        saving_throw_modifiers: tuple[RollModifier, ...] = (),
    ) -> SingleTargetSaveSpellConfirmation:
        if not source.save_ability:
            raise ValueError(f"Czar {source.name} nie ma zdefiniowanego rzutu obronnego.")
        resource_use = self.consume_action_and_source_resource(
            state,
            caster,
            spell_level=source.spell_level,
            spell_id=source.id,
            cast_level=source.cast_level,
            action_cost=source.action_cost,
            resource_pool_id=source.resource_pool_id,
            resource_cost=source.resource_cost,
        )
        caster_after = _actor_by_id(resource_use.state, str(caster.id))
        target_after = _actor_by_id(resource_use.state, str(target.id))
        saving_throw = resolve_spell_save(
            target_after,
            ability=source.save_ability,
            dc=spell_save_dc(caster_after, source),
            natural_roll=rng.randint(1, 20),
            natural_roll_2=(
                rng.randint(1, 20)
                if source.save_ability == "dexterity"
                and has_condition(
                    resource_use.state.condition_states,
                    str(target_after.id),
                    CombatCondition.RESTRAINED,
                )
                else None
            ),
            damage_on_success=source.save_damage_on_success,
            situational_modifiers=saving_throw_modifiers,
            condition_states=resource_use.state.condition_states,
            combat_actors=resource_use.state.actors,
        )
        return SingleTargetSaveSpellConfirmation(resource_use.state, resource_use, saving_throw)


class AreaSpellResolver(ActionResourceResolver):
    def confirm_area_spell(
        self,
        state: CombatState,
        *,
        caster: Actor,
        source: AttackSource,
        target_ids: tuple[str, ...],
        rng: random.Random,
        saving_throw_modifiers_by_target: Mapping[str, tuple[RollModifier, ...]] | None = None,
    ) -> AreaSpellConfirmation:
        resource_use = self.consume_action_and_source_resource(
            state,
            caster,
            spell_level=source.spell_level,
            spell_id=source.id,
            cast_level=source.cast_level,
            action_cost=source.action_cost,
            resource_pool_id=source.resource_pool_id,
            resource_cost=source.resource_cost,
        )
        saves = roll_spell_saves_for_targets(
            resource_use.state,
            caster_id=str(caster.id),
            source=source,
            target_ids=target_ids,
            rng=rng,
            saving_throw_modifiers_by_target=saving_throw_modifiers_by_target,
        )
        return AreaSpellConfirmation(resource_use.state, resource_use, saves)

    def apply_area_damage(
        self,
        state: CombatState,
        *,
        source: AttackSource,
        target_ids: tuple[str, ...],
        base_damage: int = 0,
        damage_components: tuple[DamageComponentInput, ...] | None = None,
        saving_throws: tuple[SpellSaveResult, ...] = (),
    ) -> AreaSpellDamageResolution:
        components = damage_components or (
            DamageComponentInput(
                max(0, int(base_damage)),
                DamageType(source.damage_type),
                source.name,
            ),
        )
        damage_amount = sum(component.amount for component in components)
        updated_state = state
        target_results: list[AreaSpellTargetDamage] = []
        for target_id in target_ids:
            try:
                target = _actor_by_id(updated_state, target_id)
            except ValueError:
                continue
            if target.is_defeated():
                continue
            save = spell_save_for_actor(saving_throws, target_id)
            adjusted_components = tuple(
                DamageComponentInput(
                    apply_save_damage_amount(component.amount, save),
                    component.damage_type,
                    component.label,
                )
                for component in components
            )
            damage = resolve_damage(adjusted_components)
            applied = apply_damage_result(target, damage)
            updated_state = replace_actor(updated_state, applied.actor_after)
            target_results.append(AreaSpellTargetDamage(target_id=target_id, applied_damage=applied, saving_throw=save))
        return AreaSpellDamageResolution(updated_state, source, damage_amount, tuple(target_results))


class HealingActionResolver(ActionResourceResolver):
    def apply_healing(
        self,
        state: CombatState,
        *,
        healer: Actor,
        target_id: str,
        source: HealingSource,
        amount: int,
    ) -> HealingActionResolution:
        resource_use = self.consume_action_and_source_resource(
            state,
            healer,
            spell_level=source.spell_level,
            spell_id=source.id,
            cast_level=source.cast_level,
            action_cost=source.action_cost,
        )
        target = _actor_by_id(resource_use.state, target_id)
        applied = apply_healing_result(target, source, int(amount))
        return HealingActionResolution(replace_actor(resource_use.state, applied.actor_after), resource_use, applied)


def spell_save_dc(caster: Actor, source: AttackSource) -> int:
    dc = int(source.save_dc or 0)
    if dc > 0:
        return dc
    if caster.spell_save_dc > 0:
        return caster.spell_save_dc
    raise ValueError(f"Czar {source.name} wymaga ST rzutu obronnego.")


def roll_spell_saves_for_targets(
    state: CombatState,
    *,
    caster_id: str,
    source: AttackSource,
    target_ids: tuple[str, ...],
    rng: random.Random,
    saving_throw_modifiers_by_target: Mapping[str, tuple[RollModifier, ...]] | None = None,
) -> tuple[SpellSaveResult, ...]:
    if not source.save_ability:
        return ()
    caster = _actor_by_id(state, caster_id)
    saves: list[SpellSaveResult] = []
    for target_id in target_ids:
        try:
            target = _actor_by_id(state, target_id)
        except ValueError:
            continue
        if target.is_defeated():
            continue
        saves.append(
            resolve_spell_save(
                target,
                ability=source.save_ability,
                dc=spell_save_dc(caster, source),
                natural_roll=rng.randint(1, 20),
                natural_roll_2=(
                    rng.randint(1, 20)
                    if source.save_ability == "dexterity"
                    and has_condition(
                        state.condition_states,
                        str(target.id),
                        CombatCondition.RESTRAINED,
                    )
                    else None
                ),
                damage_on_success=source.save_damage_on_success,
                situational_modifiers=(saving_throw_modifiers_by_target or {}).get(
                    target_id,
                    (),
                ),
                condition_states=state.condition_states,
                combat_actors=state.actors,
            )
        )
    return tuple(saves)


def spell_save_for_actor(saves: tuple[SpellSaveResult, ...], actor_id: str) -> SpellSaveResult | None:
    return next((save for save in saves if save.actor_id == actor_id), None)


def _actor_by_id(state: CombatState, actor_id: str) -> Actor:
    for actor in state.actors:
        if str(actor.id) == actor_id:
            return actor
    raise ValueError(f"Unknown combat actor: {actor_id}.")
