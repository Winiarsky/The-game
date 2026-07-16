from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Sequence

from dnd_board_game.actors import Actor, DeathSaveState
from dnd_board_game.world import BoardState, line_of_sight_clear

from .attack_flow import AttackSourceType, SpellCastingKind
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
    spell_level: int = 0
    casting_kind: SpellCastingKind = SpellCastingKind.NONE
    prepared: bool = True


@dataclass(frozen=True, slots=True)
class AppliedHealingResult:
    source: HealingSource
    actor_before: Actor
    actor_after: Actor
    hp_before: int
    hp_after: int
    amount: int
    effective_healing: int


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
    hp_after = min(actor.max_hp, hp_before + healing_amount)
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
