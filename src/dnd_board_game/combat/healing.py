from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor, DeathSaveState, effective_max_hit_points
from dnd_board_game.world import BoardState, line_of_sight_clear

from .attack_flow import AttackSourceType, SpellCastingKind
from .action_economy import ActionEconomyCost
from .targets import CombatTarget, actor_as_combat_target, is_public_attack_target


class HealingSourceType(StrEnum):
    SPELL = "spell"
    ITEM = "item"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class HealingSource:
    id: str
    name: str
    source_type: HealingSourceType
    range_feet: int
    healing_hint: str = ""
    healing_fixed: int | None = None
    healing_die_sides: int | None = None
    healing_modifier: int = 0
    healing_dice_count: int = 1
    spell_level: int = 0
    casting_kind: SpellCastingKind = SpellCastingKind.NONE
    prepared: bool = True
    action_cost: ActionEconomyCost = ActionEconomyCost.ACTION
    cast_level: int | None = None
    upcast_healing_dice_per_level: int = 0

    def __post_init__(self) -> None:
        if self.healing_dice_count < 1:
            raise ValueError("Healing dice count must be positive.")
        if self.upcast_healing_dice_per_level < 0:
            raise ValueError("Healing upcast dice cannot be negative.")


@dataclass(frozen=True, slots=True)
class AppliedHealingResult:
    source: HealingSource
    actor_before: Actor
    actor_after: Actor
    hp_before: int
    hp_after: int
    amount: int
    effective_healing: int


def healing_source_at_cast_level(
    source: HealingSource,
    cast_level: int,
) -> HealingSource:
    if source.spell_level <= 0:
        raise ValueError("Only a leveled spell can use a spell-slot level.")
    if cast_level < source.spell_level:
        raise ValueError("Cast level cannot be lower than the spell's base level.")
    dice_count = source.healing_dice_count + (
        cast_level - source.spell_level
    ) * source.upcast_healing_dice_per_level
    if source.healing_die_sides is None and dice_count != source.healing_dice_count:
        raise ValueError("Healing-dice upcasting requires a dice healing source.")
    if source.healing_fixed is not None:
        base = str(source.healing_fixed)
    elif source.healing_die_sides is not None:
        base = f"{dice_count}d{source.healing_die_sides}"
    else:
        base = "leczenie"
    if source.healing_modifier:
        sign = "+" if source.healing_modifier > 0 else "-"
        base = f"{base} {sign} {abs(source.healing_modifier)}"
    return replace(
        source,
        cast_level=cast_level,
        healing_dice_count=dice_count,
        healing_hint=base,
    )


def legal_healing_targets(
    board: BoardState,
    healer: Actor,
    actors: Sequence[Actor],
    source: HealingSource,
) -> tuple[CombatTarget, ...]:
    targets: list[CombatTarget] = []
    for actor in actors:
        if actor.faction != healer.faction:
            continue
        target = actor_as_combat_target(actor)
        if not is_public_healing_target(target):
            continue
        if _target_in_range(healer.position, actor.position, source.range_feet) and line_of_sight_clear(
            board, healer.position, actor.position
        ):
            targets.append(target)
    return tuple(sorted(targets, key=lambda target: (target.position.col, target.position.row, target.id)))


def apply_healing_result(actor: Actor, source: HealingSource, amount: int) -> AppliedHealingResult:
    healing_amount = max(0, int(amount))
    hp_before = actor.hp
    hp_after = min(effective_max_hit_points(actor), hp_before + healing_amount)
    actor_after = replace(
        actor,
        hp=hp_after,
        death_saves=DeathSaveState() if hp_after > 0 else actor.death_saves,
    )
    return AppliedHealingResult(
        source=source,
        actor_before=actor,
        actor_after=actor_after,
        hp_before=hp_before,
        hp_after=hp_after,
        amount=healing_amount,
        effective_healing=max(0, hp_after - hp_before),
    )


def is_public_healing_target(target: CombatTarget) -> bool:
    return target.visibility.value == "visible" and target.hp < target.max_hp


def _target_in_range(a, b, range_feet: int) -> bool:
    if range_feet <= 0:
        return False
    distance_feet = max(abs(a.col - b.col), abs(a.row - b.row)) * 5
    return distance_feet <= range_feet
