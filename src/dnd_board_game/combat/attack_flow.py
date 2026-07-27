from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor, Faction, attack_roll_modifiers
from dnd_board_game.rules import (
    AttackRollOutcome,
    AttackRollResult,
    ActiveEffect,
    D20RollRequest,
    D20RollResult,
    DiceExpression,
    resolve_attack_roll,
)
from dnd_board_game.world import BoardState, Coordinate, line_of_sight_clear
from dnd_board_game.inventory.weapons import WeaponSpecialRule

from .action_economy import ActionEconomyCost, ActionUse, consume_action
from .damage import DamageComponentSpec, DamageType
from .spells import SpellArea
from .targets import CombatTarget, actor_as_combat_target, is_public_attack_target
from .stealth import HiddenState, is_hidden_from


class AttackSourceType(StrEnum):
    WEAPON = "weapon"
    SPELL = "spell"
    ITEM = "item"
    CUSTOM = "custom"


class AttackKind(StrEnum):
    MELEE = "melee"
    RANGED = "ranged"


class SpellCastingKind(StrEnum):
    NONE = "none"
    CANTRIP = "cantrip"
    LEVELED = "leveled"


class AttackActionStatus(StrEnum):
    SELECTING_TARGET = "selecting_target"
    TARGET_SELECTED = "target_selected"
    CANCELLED = "cancelled"
    RESOLVED = "resolved"


@dataclass(frozen=True, slots=True)
class AttackSource:
    name: str
    source_type: AttackSourceType
    range_feet: int
    attack_roll_request: D20RollRequest
    damage_hint: str = ""
    damage_fixed: int | None = None
    damage_die_sides: int | None = None
    damage_modifier: int = 0
    damage_type: str = "slashing"
    damage_components: tuple[DamageComponentSpec, ...] = ()
    id: str = ""
    ability: str | None = None
    spell_level: int = 0
    area: SpellArea | None = None
    save_ability: str | None = None
    save_dc: int = 0
    save_damage_on_success: str = "none"
    casting_kind: SpellCastingKind = SpellCastingKind.NONE
    prepared: bool = True
    source_item_id: str | None = None
    attack_kind: AttackKind = AttackKind.MELEE
    proficiency_id: str | None = None
    reach_feet: int | None = None
    resource_pool_id: str | None = None
    resource_cost: int = 1
    ammunition_type: str | None = None
    loading: bool = False
    long_range_feet: int | None = None
    heavy: bool = False
    weapon_special_rule: WeaponSpecialRule | None = None
    adds_ability_modifier_to_damage: bool = False
    ability_damage_modifier_applied: int = 0
    weapon_category_id: str | None = None
    on_hit_condition: str | None = None
    limited_attacks: bool = False
    thrown: bool = False
    action_cost: ActionEconomyCost = ActionEconomyCost.ACTION
    cast_level: int | None = None
    upcast_damage_dice_per_level: int = 0

    def __post_init__(self) -> None:
        if self.upcast_damage_dice_per_level < 0:
            raise ValueError("Attack upcast damage dice cannot be negative.")
        if self.range_feet <= 0:
            raise ValueError("Attack source range_feet must be positive.")
        if self.reach_feet is not None and (
            self.reach_feet <= 0 or self.reach_feet % 5 != 0
        ):
            raise ValueError("Melee reach_feet must be a positive multiple of 5.")
        if self.resource_pool_id is not None and not self.resource_pool_id.strip():
            raise ValueError("Attack resource_pool_id cannot be empty.")
        if self.resource_cost < 1:
            raise ValueError("Attack resource_cost must be positive.")
        if self.ammunition_type is not None and not self.ammunition_type.strip():
            raise ValueError("Attack ammunition_type cannot be empty.")
        if self.ammunition_type is not None and self.attack_kind != AttackKind.RANGED:
            raise ValueError("Only ranged attacks can require ammunition.")
        if self.long_range_feet is not None:
            if self.long_range_feet <= self.range_feet:
                raise ValueError("long_range_feet must be greater than normal range.")
        components = self.damage_components
        if self.damage_fixed is not None and self.damage_die_sides is not None:
            object.__setattr__(self, "damage_die_sides", None)
        if len(components) == 1 and components[0].id == "base":
            component = components[0]
            component_die_sides = (
                component.dice.sides if component.dice is not None else None
            )
            if (
                component.fixed != self.damage_fixed
                or component_die_sides != self.damage_die_sides
                or component.modifier != self.damage_modifier
                or component.damage_type.value != self.damage_type
            ):
                components = ()
        if not components:
            fixed = self.damage_fixed
            die_sides = self.damage_die_sides
            if (
                fixed is not None
                or die_sides is not None
                or self.damage_hint
                or self.id
            ):
                components = (
                    DamageComponentSpec(
                        id="base",
                        damage_type=DamageType(self.damage_type),
                        dice=(
                            None
                            if die_sides is None or fixed is not None
                            else DiceExpression(1, die_sides)
                        ),
                        fixed=(
                            fixed
                            if fixed is not None
                            else (0 if die_sides is None else None)
                        ),
                        modifier=self.damage_modifier,
                        label=self.name,
                    ),
                )
                object.__setattr__(self, "damage_components", components)
        if len({component.id for component in components}) != len(components):
            raise ValueError("Attack damage component ids must be unique.")
        if components and not self.damage_hint:
            object.__setattr__(
                self,
                "damage_hint",
                " + ".join(component.hint() for component in components),
            )


def attack_source_at_cast_level(
    source: AttackSource,
    cast_level: int,
) -> AttackSource:
    if source.spell_level <= 0:
        raise ValueError("Only a leveled spell can use a spell-slot level.")
    if cast_level < source.spell_level:
        raise ValueError("Cast level cannot be lower than the spell's base level.")
    extra_dice = (
        cast_level - source.spell_level
    ) * source.upcast_damage_dice_per_level
    components = list(source.damage_components)
    if extra_dice:
        index = next(
            (
                index
                for index, component in enumerate(components)
                if component.dice is not None
            ),
            None,
        )
        if index is None:
            raise ValueError("Damage-dice upcasting requires a dice damage component.")
        component = components[index]
        assert component.dice is not None
        components[index] = replace(
            component,
            dice=DiceExpression(
                component.dice.count + extra_dice,
                component.dice.sides,
            ),
        )
    scaled_components = tuple(components)
    return replace(
        source,
        cast_level=cast_level,
        damage_components=scaled_components,
        damage_hint=" + ".join(component.hint() for component in scaled_components),
    )


@dataclass(frozen=True, slots=True)
class AttackActionState:
    attacker: Actor
    source: AttackSource
    legal_targets: tuple[CombatTarget, ...]
    selected_target: CombatTarget | None = None
    status: AttackActionStatus = AttackActionStatus.SELECTING_TARGET
    action_use: ActionUse = ActionUse.ACTION_AVAILABLE


@dataclass(frozen=True, slots=True)
class AttackDeclaration:
    attacker: Actor
    target: CombatTarget
    source: AttackSource


@dataclass(frozen=True, slots=True)
class AttackResolution:
    declaration: AttackDeclaration
    attack_roll: D20RollResult
    attack_roll_result: AttackRollResult
    outcome: AttackRollOutcome
    hit: bool
    critical: bool
    action_use: ActionUse


def legal_melee_targets(
    board: BoardState,
    attacker: Actor,
    actors: Sequence[Actor],
    hidden_states: Sequence[HiddenState] = (),
) -> tuple[CombatTarget, ...]:
    source = AttackSource("melee", AttackSourceType.WEAPON, 5, D20RollRequest())
    return legal_attack_targets(board, attacker, actors, source, hidden_states)


def attack_source_for_actor(source: AttackSource, actor: Actor) -> AttackSource:
    """Bind a weapon source to the current wielder's ability and proficiency profile."""

    if source.source_type != AttackSourceType.WEAPON or source.ability is None:
        return source
    proficiency_id = source.proficiency_id or source.source_item_id or source.id
    category_id = getattr(source, "weapon_category_id", None)
    proficient = actor.proficiencies.is_weapon_proficient(proficiency_id) or (
        category_id is not None
        and actor.proficiencies.is_weapon_proficient(category_id)
    )
    mode = source.attack_roll_request.mode
    modifiers = attack_roll_modifiers(
        actor,
        source.ability,
        proficient=proficient,
    )
    if source.heavy and actor.size.value == "small":
        from dnd_board_game.rules import RollMode, RollModifier, RollModifierType

        mode = (
            RollMode.NORMAL
            if mode == RollMode.ADVANTAGE
            else RollMode.DISADVANTAGE
        )
        modifiers = (
            *modifiers,
            RollModifier(
                "Ciężka broń używana przez małą istotę",
                0,
                RollModifierType.ITEM,
                stacking_key="heavy_weapon_small_wielder",
            ),
        )
    damage_modifier = source.damage_modifier
    damage_components = source.damage_components
    applied = source.ability_damage_modifier_applied
    if source.adds_ability_modifier_to_damage:
        from dnd_board_game.rules import ability_modifier

        desired = ability_modifier(getattr(actor.ability_scores, source.ability))
        delta = desired - applied
        damage_modifier += delta
        damage_components = tuple(
            replace(component, modifier=component.modifier + delta)
            if component.id == "base"
            else component
            for component in damage_components
        )
        applied = desired
    return replace(
        source,
        attack_roll_request=D20RollRequest(
            mode=mode,
            modifiers=modifiers,
        ),
        damage_modifier=damage_modifier,
        damage_components=damage_components,
        damage_hint="",
        ability_damage_modifier_applied=applied,
    )


def legal_attack_targets(
    board: BoardState,
    attacker: Actor,
    actors: Sequence[Actor],
    source: AttackSource,
    hidden_states: Sequence[HiddenState] = (),
    active_effects: tuple[ActiveEffect, ...] = (),
) -> tuple[CombatTarget, ...]:
    targets: list[CombatTarget] = []
    for actor in actors:
        if actor.id == attacker.id:
            continue
        if actor.faction == attacker.faction or actor.faction == Faction.NEUTRAL:
            continue
        if is_hidden_from(hidden_states, str(actor.id), str(attacker.id)):
            continue
        target = actor_as_combat_target(actor, active_effects)
        if not is_public_attack_target(target):
            continue
        if _target_in_range(attacker.position, actor.position, attack_range_feet(source)) and line_of_sight_clear(
            board, attacker.position, actor.position
        ):
            targets.append(target)
    return tuple(sorted(targets, key=lambda target: (target.position.col, target.position.row, target.id)))


def start_attack_action(
    board: BoardState,
    attacker: Actor,
    actors: Sequence[Actor],
    source: AttackSource,
    hidden_states: Sequence[HiddenState] = (),
    active_effects: tuple[ActiveEffect, ...] = (),
) -> AttackActionState:
    return AttackActionState(
        attacker=attacker,
        source=source,
        legal_targets=legal_attack_targets(
            board,
            attacker,
            actors,
            source,
            hidden_states,
            active_effects,
        ),
    )


def select_attack_target(
    state: AttackActionState,
    *,
    target_id: str | None = None,
    position: Coordinate | None = None,
) -> AttackActionState:
    for target in state.legal_targets:
        if target_id is not None and target.id == target_id:
            return replace(state, selected_target=target, status=AttackActionStatus.TARGET_SELECTED)
        if position is not None and target.position == position:
            return replace(state, selected_target=target, status=AttackActionStatus.TARGET_SELECTED)
    raise ValueError("Selected target is not a legal attack target.")


def cancel_attack_action(state: AttackActionState) -> AttackActionState:
    return replace(state, selected_target=None, status=AttackActionStatus.CANCELLED)


def attack_declaration_from_state(state: AttackActionState) -> AttackDeclaration:
    if state.selected_target is None:
        raise ValueError("Cannot declare an attack without a selected target.")
    return AttackDeclaration(attacker=state.attacker, target=state.selected_target, source=state.source)


def resolve_attack(declaration: AttackDeclaration, attack_roll: D20RollResult, action_use: ActionUse) -> AttackResolution:
    result = resolve_attack_roll(attack_roll, declaration.target.ac)
    used_action = consume_action(action_use)
    close_unconscious_critical = (
        result.hits
        and declaration.target.unconscious
        and _target_in_range(
            declaration.attacker.position,
            declaration.target.position,
            5,
        )
    )
    return AttackResolution(
        declaration=declaration,
        attack_roll=attack_roll,
        attack_roll_result=result,
        outcome=result.outcome,
        hit=result.hits,
        critical=result.outcome == AttackRollOutcome.CRITICAL_HIT or close_unconscious_critical,
        action_use=used_action,
    )


def _target_in_range(a: Coordinate, b: Coordinate, range_feet: int) -> bool:
    if range_feet <= 0:
        return False
    distance_feet = max(abs(a.col - b.col), abs(a.row - b.row)) * 5
    return 0 < distance_feet <= range_feet


def effective_attack_kind(source: AttackSource) -> AttackKind:
    """Return explicit attack kind, with compatibility for old long-range sources."""

    if source.attack_kind == AttackKind.RANGED:
        return AttackKind.RANGED
    if source.reach_feet is None and source.range_feet > 10:
        return AttackKind.RANGED
    return AttackKind.MELEE


def melee_reach_feet(source: AttackSource) -> int:
    if effective_attack_kind(source) != AttackKind.MELEE:
        return 0
    return int(source.reach_feet or source.range_feet or 5)


def attack_range_feet(source: AttackSource) -> int:
    if effective_attack_kind(source) == AttackKind.MELEE:
        return melee_reach_feet(source)
    return source.long_range_feet or source.range_feet
