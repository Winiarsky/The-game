from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from dnd_board_game.actors import Actor, DamageAffinityProfile, DeathSaveState
from dnd_board_game.core.damage_types import DamageType, damage_type_label_pl


class DamageAdjustment(StrEnum):
    NORMAL = "normal"
    RESISTANCE = "resistance"
    IMMUNITY = "immunity"
    VULNERABILITY = "vulnerability"
    RESISTANCE_AND_VULNERABILITY = "resistance_and_vulnerability"


@dataclass(frozen=True, slots=True)
class DamageComponentInput:
    amount: int
    damage_type: DamageType
    label: str = ""

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Damage amount cannot be negative.")


@dataclass(frozen=True, slots=True)
class ResolvedDamageComponent:
    damage_type: DamageType
    amount_before: int
    amount_applied: int
    adjustment: DamageAdjustment = DamageAdjustment.NORMAL
    label: str = ""

    @property
    def changed(self) -> bool:
        return self.amount_before != self.amount_applied

    def as_payload(self) -> dict[str, object]:
        return {
            "damage_type": self.damage_type.value,
            "damage_type_label": damage_type_label_pl(self.damage_type),
            "amount_before": self.amount_before,
            "amount_applied": self.amount_applied,
            "adjustment": self.adjustment.value,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class DamageResult:
    components: tuple[DamageComponentInput, ...]
    resolved_components: tuple[ResolvedDamageComponent, ...]
    total_before_reduction: int
    total_applied: int

    @property
    def reduced_or_amplified(self) -> bool:
        return self.total_before_reduction != self.total_applied

    def as_payload(self) -> dict[str, object]:
        return {
            "total_before_reduction": self.total_before_reduction,
            "total_applied": self.total_applied,
            "components": [component.as_payload() for component in self.resolved_components],
        }


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
    death_save_failures_added: int = 0
    instant_death: bool = False


def resolve_damage(
    components: tuple[DamageComponentInput, ...],
    affinities: DamageAffinityProfile | None = None,
) -> DamageResult:
    profile = affinities or DamageAffinityProfile()
    grouped = _group_components_by_type(components)
    resolved = tuple(_resolve_component(component, profile) for component in grouped)
    return DamageResult(
        components=components,
        resolved_components=resolved,
        total_before_reduction=sum(component.amount for component in components),
        total_applied=sum(component.amount_applied for component in resolved),
    )


def apply_damage_result(
    actor: Actor,
    damage: DamageResult,
    *,
    critical: bool = False,
) -> AppliedDamageResult:
    damage = resolve_damage(damage.components, actor.damage_affinities)
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
    death_saves = actor.death_saves
    failures_added = 0
    instant_death = False
    if actor.uses_death_saves and not actor.death_saves.dead:
        if hp_before > 0 and hp == 0:
            excess_damage = max(0, remaining - hp_before)
            instant_death = excess_damage >= actor.max_hp
            death_saves = DeathSaveState(dead=True) if instant_death else DeathSaveState()
        elif hp_before == 0 and remaining > 0:
            instant_death = remaining >= actor.max_hp
            if instant_death:
                death_saves = DeathSaveState(dead=True)
            else:
                failures_added = 2 if critical else 1
                failures = min(3, actor.death_saves.failures + failures_added)
                death_saves = DeathSaveState(
                    successes=actor.death_saves.successes,
                    failures=failures,
                    dead=failures >= 3,
                )
    actor_after = replace(actor, hp=hp, temp_hp=temp_hp, death_saves=death_saves)
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
        death_save_failures_added=failures_added,
        instant_death=instant_death,
    )


def apply_damage(actor: Actor, damage: DamageResult, *, critical: bool = False) -> Actor:
    return apply_damage_result(actor, damage, critical=critical).actor_after


def _group_components_by_type(
    components: tuple[DamageComponentInput, ...],
) -> tuple[DamageComponentInput, ...]:
    amounts: dict[DamageType, int] = {}
    labels: dict[DamageType, list[str]] = {}
    for component in components:
        amounts[component.damage_type] = amounts.get(component.damage_type, 0) + component.amount
        if component.label and component.label not in labels.setdefault(component.damage_type, []):
            labels[component.damage_type].append(component.label)
    return tuple(
        DamageComponentInput(
            amount,
            damage_type,
            " + ".join(labels.get(damage_type, ())),
        )
        for damage_type, amount in amounts.items()
    )


def _resolve_component(
    component: DamageComponentInput,
    affinities: DamageAffinityProfile,
) -> ResolvedDamageComponent:
    resistant = affinities.is_resistant_to(component.damage_type)
    immune = affinities.is_immune_to(component.damage_type)
    vulnerable = affinities.is_vulnerable_to(component.damage_type)
    amount = component.amount
    if immune:
        adjustment = DamageAdjustment.IMMUNITY
        amount = 0
    elif resistant and vulnerable:
        adjustment = DamageAdjustment.RESISTANCE_AND_VULNERABILITY
        amount = (amount // 2) * 2
    elif resistant:
        adjustment = DamageAdjustment.RESISTANCE
        amount //= 2
    elif vulnerable:
        adjustment = DamageAdjustment.VULNERABILITY
        amount *= 2
    else:
        adjustment = DamageAdjustment.NORMAL
    return ResolvedDamageComponent(
        damage_type=component.damage_type,
        amount_before=component.amount,
        amount_applied=amount,
        adjustment=adjustment,
        label=component.label,
    )
