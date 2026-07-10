from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor


class DamageType(StrEnum):
    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    FORCE = "force"
    NECROTIC = "necrotic"
    RADIANT = "radiant"
    POISON = "poison"
    PSYCHIC = "psychic"
    THUNDER = "thunder"
    LIGHTNING = "lightning"
    ACID = "acid"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class DamageComponentInput:
    amount: int
    damage_type: DamageType
    label: str = ""

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Damage amount cannot be negative.")


@dataclass(frozen=True, slots=True)
class DamageResult:
    components: tuple[DamageComponentInput, ...]
    total_before_reduction: int
    total_applied: int


@dataclass(frozen=True, slots=True)
class AppliedDamageResult:
    damage: DamageResult
    actor_before: Actor
    actor_after: Actor
    hp_before: int
    hp_after: int
    temp_hp_before: int
    temp_hp_after: int
    absorbed_by_temp_hp: int
    applied_to_hp: int
    defeated: bool
    defeated_by_damage: bool


def resolve_damage(components: tuple[DamageComponentInput, ...]) -> DamageResult:
    total = sum(component.amount for component in components)
    return DamageResult(components=components, total_before_reduction=total, total_applied=total)


def apply_damage_result(actor: Actor, damage: DamageResult) -> AppliedDamageResult:
    remaining = damage.total_applied
    temp_hp_before = actor.temp_hp
    hp_before = actor.hp
    temp_hp = temp_hp_before
    hp = hp_before
    absorbed = 0
    if temp_hp_before > 0:
        absorbed = min(temp_hp_before, remaining)
        temp_hp -= absorbed
        remaining -= absorbed
    applied_to_hp = 0
    if remaining > 0:
        applied_to_hp = min(hp, remaining)
        hp = max(0, hp - remaining)
    actor_after = replace(actor, hp=hp, temp_hp=temp_hp)
    return AppliedDamageResult(
        damage=damage,
        actor_before=actor,
        actor_after=actor_after,
        hp_before=hp_before,
        hp_after=hp,
        temp_hp_before=temp_hp_before,
        temp_hp_after=temp_hp,
        absorbed_by_temp_hp=absorbed,
        applied_to_hp=applied_to_hp,
        defeated=actor_after.is_defeated(),
        defeated_by_damage=not actor.is_defeated() and actor_after.is_defeated(),
    )


def apply_damage(actor: Actor, damage: DamageResult) -> Actor:
    return apply_damage_result(actor, damage).actor_after
