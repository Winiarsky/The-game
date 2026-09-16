"""Deterministic combat rules for Garran's board-game archetype."""

from __future__ import annotations

from dnd_board_game.actors.resources import uses_physical_mana, uses_shared_mana

from dataclasses import dataclass, replace
from typing import Sequence

from dnd_board_game.actors import (
    Actor,
    Faction,
    actor_has_feature,
    can_spend_actor_resource,
    spend_actor_resource,
)
from dnd_board_game.core.damage_types import DamageType
from dnd_board_game.rules import (
    ActiveEffect,
    AdditionalEffectExpiration,
    EffectDuration,
    EffectSource,
    EffectSourceType,
    SavingThrowRequest,
    ability_modifier,
    apply_active_effect,
)
from dnd_board_game.world import BoardState, Coordinate

from .action_economy import ActionEconomyCost
from .auras import strongest_aura_members
from .conditions import CombatCondition, remove_condition
from .damage import DamageComponentInput, AppliedDamageResult, apply_damage_result, resolve_damage
from .session import (
    CombatState,
    current_actor,
    replace_actor,
    use_action_economy_cost,
    use_movement_action,
)
from .spells import SavingThrowResult, grid_distance_feet, resolve_actor_saving_throw


TACTIC_FEATURE_IDS = frozenset(
    {
        "garran_command_halt",
        "garran_shield_wall",
        "garran_rally",
        "garran_guard_companion",
    }
)


@dataclass(frozen=True, slots=True)
class GarranFeatureResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    actor_before: Actor
    actor_after: Actor
    feature_id: str
    target_actor_id: str | None = None


@dataclass(frozen=True, slots=True)
class ShieldBashResolution:
    state: CombatState
    attacker: Actor
    target_before: Actor
    target_after: Actor
    attacker_total: int
    defender_total: int
    damage: AppliedDamageResult | None
    push_destination: Coordinate | None

    @property
    def succeeded(self) -> bool:
        return self.attacker_total > self.defender_total


@dataclass(frozen=True, slots=True)
class CommandHaltResolution:
    state: CombatState
    active_effects: tuple[ActiveEffect, ...]
    target: Actor
    saving_throw: SavingThrowResult
    outcome: str


@dataclass(frozen=True, slots=True)
class GuardRedirect:
    target: Actor
    active_effects: tuple[ActiveEffect, ...]
    redirected: bool
    protected_actor_id: str | None = None


def _source(feature_id: str, label: str) -> EffectSource:
    return EffectSource(EffectSourceType.ACTION, feature_id, label)


def _spend_tactic_and_action(
    state: CombatState,
    cost: ActionEconomyCost,
) -> tuple[CombatState, Actor, Actor]:
    actor = current_actor(state)
    if not can_spend_actor_resource(actor, "tactics_uses"):
        raise ValueError("Brak punktów Taktyki.")
    action = use_action_economy_cost(state, cost)
    if not action.accepted:
        raise ValueError(action.message)
    actor_after_action = current_actor(action.state)
    spent = spend_actor_resource(actor_after_action, "tactics_uses")
    return replace_actor(action.state, spent.actor_after), actor, spent.actor_after


def resolve_garran_defensive_stance(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> GarranFeatureResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "defensive_stance"):
        raise ValueError("Aktywna postać nie posiada Pozycji obronnej.")
    movement = (use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
                if uses_physical_mana(actor) else use_movement_action(state, actor))
    if not movement.accepted:
        raise ValueError(movement.message)
    effect = ActiveEffect(
        id=f"garran_defensive_stance:{actor.id}",
        actor_id=str(actor.id),
        kind="garran_defensive_stance_ac",
        label="Pozycja obronna",
        object_id="class_feature:defensive_stance",
        value=2,
        anchor_position=actor.position,
        source_actor_id=str(actor.id),
        source=_source("defensive_stance", "Pozycja obronna"),
        duration=EffectDuration.UNTIL_TURN_START,
        expiration_actor_id=str(actor.id),
        additional_expirations=(
            AdditionalEffectExpiration(
                EffectDuration.WHILE_AT_POSITION,
                actor_id=str(actor.id),
            ),
        ),
    )
    effects = apply_active_effect(active_effects, effect).active_effects
    return GarranFeatureResolution(
        movement.state, effects, actor, current_actor(movement.state), "defensive_stance"
    )


def shield_bash_destination(
    board: BoardState,
    state: CombatState,
    attacker: Actor,
    target: Actor,
) -> Coordinate | None:
    from .shared_mana_features import state_blocks_forced_movement
    if state_blocks_forced_movement(state, target):
        return None
    dc = target.position.col - attacker.position.col
    dr = target.position.row - attacker.position.row
    if max(abs(dc), abs(dr)) != 1:
        return None
    destination = Coordinate(target.position.col + dc, target.position.row + dr)
    if not board.in_bounds(destination) or board.terrain_at(destination).blocks_movement:
        return None
    if abs(dc) + abs(dr) == 1 and board.blocks_edge(target.position, destination):
        return None
    if any(
        other.id != target.id
        and not other.is_defeated()
        and other.position == destination
        for other in state.actors
    ):
        return None
    return destination


def resolve_shield_bash(
    state: CombatState,
    *,
    board: BoardState,
    target_id: str,
    attacker_roll: int,
    defender_roll: int,
    damage_roll: int,
) -> ShieldBashResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "shield_bash"):
        raise ValueError("Aktywna postać nie posiada Uderzenia tarczą.")
    target = next((item for item in state.actors if str(item.id) == target_id), None)
    if target is None or target.faction == actor.faction or target.is_defeated():
        raise ValueError("Uderzenie tarczą wymaga żywego przeciwnika.")
    if grid_distance_feet(actor.position, target.position) > 5:
        raise ValueError("Cel Uderzenia tarczą musi znajdować się w odległości 5 stóp.")
    if not 1 <= attacker_roll <= 20 or not 1 <= defender_roll <= 20:
        raise ValueError("Rzuty sporne muszą mieścić się w zakresie 1–20.")
    count = 1 + (dict(state.shared_mana.pending_boosts).get("damage", 0) if state.shared_mana else 0)
    if type(damage_roll) is not int or not count <= damage_roll <= 6 * count:
        raise ValueError(f"Podaj sumę {count}k6 obrażeń Uderzenia tarczą.")
    action = use_action_economy_cost(state, ActionEconomyCost.BONUS_ACTION)
    if not action.accepted:
        raise ValueError(action.message)
    from .mana_charge import state_charge_bonus
    attacker_total = attacker_roll + ability_modifier(actor.ability_scores.strength) + state_charge_bonus(state, actor)
    defender_total = defender_roll + ability_modifier(target.ability_scores.strength) + state_charge_bonus(state, target)
    if attacker_total <= defender_total:
        return ShieldBashResolution(
            action.state, actor, target, target, attacker_total, defender_total, None, None
        )
    damage = apply_damage_result(
        target,
        resolve_damage(
            (
                DamageComponentInput(
                    max(0, damage_roll + ability_modifier(actor.ability_scores.strength)),
                    DamageType.BLUDGEONING,
                    "Uderzenie tarczą",
                ),
            ),
            target.damage_affinities,
        ),
    )
    destination = shield_bash_destination(board, action.state, actor, target)
    target_after = replace(
        damage.actor_after,
        position=destination or damage.actor_after.position,
    )
    updated = replace_actor(action.state, target_after)
    return ShieldBashResolution(
        updated,
        actor,
        target,
        target_after,
        attacker_total,
        defender_total,
        damage,
        destination,
    )


def resolve_garran_command_halt(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    target_id: str,
    natural_roll: int,
    natural_roll_2: int | None = None,
) -> CommandHaltResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "garran_command_halt"):
        raise ValueError("Aktywna postać nie posiada Rozkazu: Stać.")
    target = next((item for item in state.actors if str(item.id) == target_id), None)
    if target is None or target.faction == actor.faction or target.is_defeated():
        raise ValueError("Rozkaz wymaga żywego przeciwnika.")
    if grid_distance_feet(actor.position, target.position) > 60:
        raise ValueError("Cel Rozkazu znajduje się poza zasięgiem 60 stóp.")
    updated, _, _ = _spend_tactic_and_action(state, ActionEconomyCost.ACTION)
    saving_throw = resolve_actor_saving_throw(
        target,
        SavingThrowRequest(
            ability="wisdom",
            dc=14,
            source_label="Rozkaz: Stać",
            dc_source_label="ST Taktyki",
        ),
        natural_roll=natural_roll,
        natural_roll_2=natural_roll_2,
        condition_states=updated.condition_states,
        combat_actors=updated.actors,
        active_effects=active_effects,
    )
    if uses_shared_mana(actor):
        if saving_throw.success:
            return CommandHaltResolution(updated, active_effects, target, saving_throw, "success")
        slow = ActiveEffect(id=f"garran_command_half_movement:{target.id}", actor_id=str(target.id),
            kind="garran_command_half_movement", label="Rozkaz: Stać", object_id="class_feature:garran_command_halt", value=0,
            source_actor_id=str(actor.id), duration=EffectDuration.UNTIL_TURN_START, expiration_actor_id=str(actor.id))
        from .conditions import apply_condition
        conditions = apply_condition(updated.condition_states, target, CombatCondition.NO_REACTIONS,
            source_actor_id=str(actor.id), source_spell_id="garran_command_halt", source_spell_level=0, source_label="Rozkaz: Stać",
            duration=EffectDuration.UNTIL_TURN_START, expiration_actor_id=str(actor.id)).condition_states
        return CommandHaltResolution(replace(updated, condition_states=conditions),
            apply_active_effect(active_effects, slow).active_effects, target, saving_throw, "failure")
    if natural_roll == 20:
        outcome = "critical_success"
        effects = active_effects
    else:
        effective_success = saving_throw.success and natural_roll != 1
        outcome = (
            "critical_failure"
            if natural_roll == 1
            else "success"
            if effective_success
            else "failure"
        )
        kind = (
            "garran_command_half_movement"
            if effective_success
            else "garran_command_no_movement"
        )
        effect = ActiveEffect(
            id=f"{kind}:{target.id}",
            actor_id=str(target.id),
            kind=kind,
            label="Rozkaz: Stać",
            object_id="class_feature:garran_command_halt",
            value=0,
            source_actor_id=str(actor.id),
            source=_source("garran_command_halt", "Rozkaz: Stać"),
            duration=EffectDuration.UNTIL_TURN_END,
            expiration_actor_id=str(target.id),
        )
        effects = apply_active_effect(active_effects, effect).active_effects
        if natural_roll == 1:
            penalty = replace(
                effect,
                id=f"garran_command_attack_penalty:{target.id}",
                kind="garran_command_attack_penalty",
                label="Rozkaz: zachwianie",
                value=-2,
                stacking_key=f"{target.id}:garran_command_attack_penalty",
            )
            effects = apply_active_effect(effects, penalty).active_effects
    return CommandHaltResolution(updated, effects, target, saving_throw, outcome)


def resolve_garran_shield_wall(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> GarranFeatureResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "garran_shield_wall"):
        raise ValueError("Aktywna postać nie posiada Osłony tarczą.")
    updated, before, after = _spend_tactic_and_action(state, ActionEconomyCost.BONUS_ACTION)
    source_effect = ActiveEffect(
        id=f"garran_shield_wall_source:{actor.id}",
        actor_id=str(actor.id),
        kind="garran_shield_wall_source",
        label="Osłona tarczą",
        object_id="class_feature:garran_shield_wall",
        value=2,
        source_actor_id=str(actor.id),
        source=_source("garran_shield_wall", "Osłona tarczą"),
        duration=EffectDuration.UNTIL_TURN_START,
        expiration_actor_id=str(actor.id),
        radius_feet=5,
    )
    effects = apply_active_effect(active_effects, source_effect).active_effects
    effects = synchronize_garran_effects(updated.actors, effects)
    return GarranFeatureResolution(updated, effects, before, after, "garran_shield_wall")


def resolve_garran_rally(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
) -> GarranFeatureResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "garran_rally"):
        raise ValueError("Aktywna postać nie posiada Mowy dowódcy.")
    updated, before, after = _spend_tactic_and_action(state, ActionEconomyCost.ACTION)
    effects = active_effects
    conditions = updated.condition_states
    for ally in updated.actors:
        if ally.faction != actor.faction or ally.is_defeated():
            continue
        if grid_distance_feet(actor.position, ally.position) > (15 if uses_shared_mana(actor) else 30):
            continue
        if any(
            item.actor_id == str(ally.id) and item.condition == CombatCondition.DEAFENED
            for item in conditions
        ):
            continue
        conditions = remove_condition(conditions, str(ally.id), CombatCondition.FRIGHTENED)
        advantage = ActiveEffect(
            id=f"garran_rally_advantage:{ally.id}",
            actor_id=str(ally.id),
            kind="garran_rally_advantage",
            label="Mowa dowódcy",
            object_id="class_feature:garran_rally",
            value=1,
            source_actor_id=str(actor.id),
            source=_source("garran_rally", "Mowa dowódcy"),
            duration=EffectDuration.UNTIL_TURN_END,
            expiration_actor_id=str(ally.id),
        )
        effects = apply_active_effect(effects, advantage).active_effects
    updated = replace(updated, condition_states=conditions)
    return GarranFeatureResolution(updated, effects, before, after, "garran_rally")


def resolve_garran_guard_companion(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    *,
    target_id: str,
) -> GarranFeatureResolution:
    actor = current_actor(state)
    if not actor_has_feature(actor, "garran_guard_companion"):
        raise ValueError("Aktywna postać nie posiada Osłony towarzysza.")
    target = next((item for item in state.actors if str(item.id) == target_id), None)
    if target is None or target.id == actor.id or target.faction != actor.faction or target.is_defeated():
        raise ValueError("Osłona towarzysza wymaga żywego sojusznika.")
    if grid_distance_feet(actor.position, target.position) > 5:
        raise ValueError("Chroniony sojusznik musi sąsiadować z Garranem.")
    updated, before, after = _spend_tactic_and_action(state, ActionEconomyCost.ACTION)
    retained = tuple(
        effect
        for effect in active_effects
        if not (
            effect.kind == "garran_guard_companion"
            and effect.source_actor_id == str(actor.id)
        )
    )
    effect = ActiveEffect(
        id=f"garran_guard_companion:{actor.id}:{target.id}",
        actor_id=str(target.id),
        kind="garran_guard_companion",
        label=f"Osłona Garrana: {target.name}",
        object_id="class_feature:garran_guard_companion",
        value=0,
        source_actor_id=str(actor.id),
        target_actor_id=str(target.id),
        source=_source("garran_guard_companion", "Osłona towarzysza"),
        duration=EffectDuration.UNTIL_ENCOUNTER_END,
    )
    effects = apply_active_effect(retained, effect).active_effects
    return GarranFeatureResolution(updated, effects, before, after, "garran_guard_companion", str(target.id))


def synchronize_garran_effects(
    actors: Sequence[Actor],
    active_effects: Sequence[ActiveEffect],
) -> tuple[ActiveEffect, ...]:
    actor_by_id = {str(actor.id): actor for actor in actors}
    retained: list[ActiveEffect] = []
    sources: list[ActiveEffect] = []
    members: list[ActiveEffect] = []
    for effect in active_effects:
        if effect.kind == "warding_bond" and effect.source_actor_id == "garran":
            # Compatibility cleanup for encounters restored from the retired
            # spell-shaped Garran deck.
            continue
        if effect.kind == "garran_shield_wall_member":
            continue
        if effect.kind == "garran_guard_companion":
            protector = actor_by_id.get(effect.source_actor_id or "")
            protected = actor_by_id.get(effect.actor_id)
            if (
                protector is None
                or protected is None
                or protector.is_defeated()
                or protected.is_defeated()
                or grid_distance_feet(protector.position, protected.position) > 5
            ):
                continue
        retained.append(effect)
        if effect.kind == "garran_shield_wall_source":
            sources.append(effect)
    for source in sources:
        protector = actor_by_id.get(source.actor_id)
        if protector is None or protector.is_defeated():
            continue
        for ally in actors:
            if ally.id == protector.id or ally.faction != protector.faction or ally.is_defeated():
                continue
            if grid_distance_feet(protector.position, ally.position) > 5:
                continue
            members.append(
                ActiveEffect(
                    id=f"garran_shield_wall_member:{protector.id}:{ally.id}",
                    actor_id=str(ally.id),
                    kind="garran_shield_wall_member",
                    label="Osłona tarczą Garrana",
                    object_id="class_feature:garran_shield_wall",
                    value=source.value,
                    source_actor_id=str(protector.id),
                    source=source.source,
                    duration=source.duration,
                    expiration_actor_id=source.expiration_actor_id,
                )
            )
    return (*retained, *strongest_aura_members(members))


def redirect_guarded_single_target(
    state: CombatState,
    active_effects: tuple[ActiveEffect, ...],
    intended_target_id: str,
) -> GuardRedirect:
    effects = synchronize_garran_effects(state.actors, active_effects)
    guard = next(
        (
            effect
            for effect in effects
            if effect.kind == "garran_guard_companion"
            and effect.actor_id == intended_target_id
        ),
        None,
    )
    intended = next(actor for actor in state.actors if str(actor.id) == intended_target_id)
    if guard is None:
        return GuardRedirect(intended, effects, False)
    protector = next(
        (actor for actor in state.actors if str(actor.id) == guard.source_actor_id),
        None,
    )
    if protector is None or protector.is_defeated():
        return GuardRedirect(intended, tuple(effect for effect in effects if effect.id != guard.id), False)
    remaining = tuple(effect for effect in effects if effect.id != guard.id)
    return GuardRedirect(protector, remaining, True, intended_target_id)


__all__ = [
    "CommandHaltResolution",
    "GarranFeatureResolution",
    "GuardRedirect",
    "ShieldBashResolution",
    "TACTIC_FEATURE_IDS",
    "redirect_guarded_single_target",
    "resolve_garran_command_halt",
    "resolve_garran_defensive_stance",
    "resolve_garran_guard_companion",
    "resolve_garran_rally",
    "resolve_garran_shield_wall",
    "resolve_shield_bash",
    "shield_bash_destination",
    "synchronize_garran_effects",
]
