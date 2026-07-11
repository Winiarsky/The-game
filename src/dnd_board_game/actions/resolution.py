from __future__ import annotations

import random
from dataclasses import dataclass

from dnd_board_game.actors import Actor
from dnd_board_game.combat import (
    AppliedDamageResult,
    AppliedHealingResult,
    AttackSource,
    CombatState,
    DamageComponentInput,
    DamageType,
    HealingSource,
    SpellSaveResult,
    apply_damage_result,
    apply_healing_result,
    apply_save_damage_amount,
    consume_spell_resource,
    replace_actor,
    resolve_damage,
    resolve_spell_save,
    use_turn_action,
)


@dataclass(frozen=True, slots=True)
class ActionResourceResolution:
    state: CombatState
    actor_before: Actor
    actor_after: Actor
    spell_level: int
    spell_resource_consumed: bool


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
    ) -> ActionResourceResolution:
        action_result = use_turn_action(state)
        if not action_result.accepted:
            raise ValueError(action_result.message)
        state_after_action = action_result.state
        actor_after_action = _actor_by_id(state_after_action, str(actor.id))
        resource_result = consume_spell_resource(actor_after_action, int(spell_level))
        state_after_resource = state_after_action
        if resource_result.consumed:
            state_after_resource = replace_actor(state_after_action, resource_result.actor_after)
        return ActionResourceResolution(
            state=state_after_resource,
            actor_before=actor,
            actor_after=resource_result.actor_after,
            spell_level=int(spell_level),
            spell_resource_consumed=resource_result.consumed,
        )


class AttackActionResolver(ActionResourceResolver):
    def apply_target_damage(
        self,
        state: CombatState,
        *,
        target_id: str,
        source: AttackSource,
        base_damage: int,
        saving_throw: SpellSaveResult | None = None,
    ) -> SingleTargetDamageResolution:
        target = _actor_by_id(state, target_id)
        applied_amount = apply_save_damage_amount(max(0, int(base_damage)), saving_throw)
        damage = resolve_damage((DamageComponentInput(applied_amount, DamageType(source.damage_type), source.name),))
        applied = apply_damage_result(target, damage)
        return SingleTargetDamageResolution(
            state=replace_actor(state, applied.actor_after),
            target_id=target_id,
            base_damage=max(0, int(base_damage)),
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
    ) -> SingleTargetSaveSpellConfirmation:
        if not source.save_ability:
            raise ValueError(f"Czar {source.name} nie ma zdefiniowanego rzutu obronnego.")
        resource_use = self.consume_action_and_source_resource(state, caster, spell_level=source.spell_level)
        caster_after = _actor_by_id(resource_use.state, str(caster.id))
        target_after = _actor_by_id(resource_use.state, str(target.id))
        saving_throw = resolve_spell_save(
            target_after,
            ability=source.save_ability,
            dc=spell_save_dc(caster_after, source),
            natural_roll=rng.randint(1, 20),
            damage_on_success=source.save_damage_on_success,
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
    ) -> AreaSpellConfirmation:
        resource_use = self.consume_action_and_source_resource(state, caster, spell_level=source.spell_level)
        saves = roll_spell_saves_for_targets(resource_use.state, caster_id=str(caster.id), source=source, target_ids=target_ids, rng=rng)
        return AreaSpellConfirmation(resource_use.state, resource_use, saves)

    def apply_area_damage(
        self,
        state: CombatState,
        *,
        source: AttackSource,
        target_ids: tuple[str, ...],
        base_damage: int,
        saving_throws: tuple[SpellSaveResult, ...] = (),
    ) -> AreaSpellDamageResolution:
        damage_amount = max(0, int(base_damage))
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
            applied_amount = apply_save_damage_amount(damage_amount, save)
            damage = resolve_damage((DamageComponentInput(applied_amount, DamageType(source.damage_type), source.name),))
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
        resource_use = self.consume_action_and_source_resource(state, healer, spell_level=source.spell_level)
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
                damage_on_success=source.save_damage_on_success,
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
