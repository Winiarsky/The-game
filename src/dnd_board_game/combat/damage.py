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


def resolve_damage(components: tuple[DamageComponentInput, ...]) -> DamageResult:
    total = sum(component.amount for component in components)
    return DamageResult(components=components, total_before_reduction=total, total_applied=total)


def apply_damage(actor: Actor, damage: DamageResult) -> Actor:
    remaining = damage.total_applied
    temp_hp = actor.temp_hp
    hp = actor.hp
    if temp_hp > 0:
        absorbed = min(temp_hp, remaining)
        temp_hp -= absorbed
        remaining -= absorbed
    if remaining > 0:
        hp = max(0, hp - remaining)
    return replace(actor, hp=hp, temp_hp=temp_hp)
