from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from collections.abc import Callable, Mapping

from dnd_board_game.actors import (
    Actor,
    DamageAffinityProfile,
    DeathSaveState,
    effective_max_hit_points,
    actor_has_feature,
    can_spend_actor_resource,
    spend_actor_resource,
)
from dnd_board_game.core.damage_types import DamageType, damage_type_label_pl
from dnd_board_game.rules import DiceExpression


class DamageAdjustment(StrEnum):
    NORMAL = "normal"
    RESISTANCE = "resistance"
    IMMUNITY = "immunity"
    VULNERABILITY = "vulnerability"
    RESISTANCE_AND_VULNERABILITY = "resistance_and_vulnerability"


@dataclass(frozen=True, slots=True)
class DamageComponentSpec:
    """Authored damage formula for one independently typed component."""

    id: str
    damage_type: DamageType
    dice: DiceExpression | None = None
    fixed: int | None = None
    modifier: int = 0
    label: str = ""
    critical_bonus_dice: int = 0

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Damage component id cannot be empty.")
        if (self.dice is None) == (self.fixed is None):
            raise ValueError(
                "Damage component requires exactly one of dice or fixed."
            )
        if self.fixed is not None and self.fixed < 0:
            raise ValueError("Fixed damage cannot be negative.")
        if self.critical_bonus_dice < 0:
            raise ValueError("Critical bonus dice cannot be negative.")

    def formula(self, *, critical: bool = False) -> str:
        if self.dice is not None:
            dice_count = self.dice.count * (2 if critical else 1)
            if critical:
                dice_count += self.critical_bonus_dice
            base = f"{dice_count}d{self.dice.sides}"
        else:
            base = str(self.fixed)
        if self.modifier:
            sign = "+" if self.modifier > 0 else "-"
            base = f"{base} {sign} {abs(self.modifier)}"
        return base

    def hint(self, *, critical: bool = False) -> str:
        label = self.label.strip()
        prefix = f"{label}: " if label else ""
        return (
            f"{prefix}{self.formula(critical=critical)} "
            f"{damage_type_label_pl(self.damage_type)}"
        )

    def as_payload(self, *, critical: bool = False) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "damage_type": self.damage_type.value,
            "damage_type_label": damage_type_label_pl(self.damage_type),
            "dice": (
                (
                    f"{self.dice.count * (2 if critical else 1) + (self.critical_bonus_dice if critical else 0)}"
                    f"d{self.dice.sides}"
                )
                if self.dice is not None
                else None
            ),
            "fixed": self.fixed,
            "modifier": self.modifier,
            "formula": self.formula(critical=critical),
            "hint": self.hint(critical=critical),
        }


@dataclass(frozen=True, slots=True)
class DamageComponentInput:
    amount: int
    damage_type: DamageType
    label: str = ""

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Damage amount cannot be negative.")


def roll_damage_components(
    components: tuple[DamageComponentSpec, ...],
    roll_die: Callable[[int], int],
    *,
    critical: bool = False,
) -> tuple[DamageComponentInput, ...]:
    """Roll authored components, doubling only dice on a critical hit."""

    results: list[DamageComponentInput] = []
    for component in components:
        if component.dice is not None:
            dice_count = component.dice.count * (2 if critical else 1)
            if critical:
                dice_count += component.critical_bonus_dice
            rolls = DiceExpression(dice_count, component.dice.sides).roll(roll_die)
            amount = sum(rolls) + component.modifier
        else:
            amount = int(component.fixed or 0) + component.modifier
        results.append(
            DamageComponentInput(
                max(0, amount),
                component.damage_type,
                component.label or component.id,
            )
        )
    return tuple(results)


def damage_components_from_totals(
    components: tuple[DamageComponentSpec, ...],
    totals: Mapping[str, int],
) -> tuple[DamageComponentInput, ...]:
    expected_ids = {component.id for component in components}
    unknown_ids = set(totals) - expected_ids
    if unknown_ids:
        raise ValueError(
            "Unknown damage component ids: " + ", ".join(sorted(unknown_ids)) + "."
        )
    missing_ids = expected_ids - set(totals)
    if missing_ids:
        raise ValueError(
            "Missing damage component totals: " + ", ".join(sorted(missing_ids)) + "."
        )
    return tuple(
        DamageComponentInput(
            int(totals[component.id]),
            component.damage_type,
            component.label or component.id,
        )
        for component in components
    )


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
    active_effects: tuple[object, ...] = (),
    combat_actors: tuple[Actor, ...] = (),
) -> AppliedDamageResult:
    if active_effects:
        from .poison_protection import poison_protection_affinities

        affinities = poison_protection_affinities(actor, active_effects)
        raging_without_heavy_armor = (
            any(
                getattr(effect, "actor_id", "") == str(actor.id)
                and getattr(effect, "kind", "") == "rage"
                for effect in active_effects
            )
            and not any(
                item.equipped
                and getattr(getattr(item, "armor_category", None), "value", "") == "heavy"
                for item in actor.inventory
            )
        )
        if raging_without_heavy_armor:
            affinities = DamageAffinityProfile(
                resistances=(
                    *affinities.resistances,
                    DamageType.BLUDGEONING,
                    DamageType.PIERCING,
                    DamageType.SLASHING,
                ),
                immunities=affinities.immunities,
                vulnerabilities=affinities.vulnerabilities,
            )
        if combat_actors:
            from .warding_bond import warding_bond_affinities

            affinities = warding_bond_affinities(
                actor,
                active_effects,
                combat_actors,
                affinities,
            )
    else:
        affinities = actor.damage_affinities
    damage = resolve_damage(damage.components, affinities)
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
    actor_base = actor
    wild_shape_overflow = 0
    normal_form_hp_before = 0
    if actor.wild_shape is not None and hp == 0:
        from .class_feature_rules import revert_wild_shape

        wild_shape_overflow = max(0, remaining - hp_before)
        actor_base = revert_wild_shape(actor)
        normal_form_hp_before = actor_base.hp
        hp = max(0, normal_form_hp_before - wild_shape_overflow)
    death_saves = actor.death_saves
    failures_added = 0
    instant_death = False
    if actor.uses_death_saves and not actor.death_saves.dead:
        if hp_before > 0 and hp == 0:
            excess_damage = (
                max(0, wild_shape_overflow - normal_form_hp_before)
                if actor.wild_shape is not None
                else max(0, remaining - hp_before)
            )
            instant_death = excess_damage >= effective_max_hit_points(actor_base)
            death_saves = DeathSaveState(dead=True) if instant_death else DeathSaveState()
        elif hp_before == 0 and remaining > 0:
            instant_death = remaining >= effective_max_hit_points(actor)
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
    actor_after = replace(
        actor_base,
        hp=hp,
        temp_hp=temp_hp,
        death_saves=death_saves,
    )
    if (
        hp_before > 0
        and hp == 0
        and not instant_death
        and actor_has_feature(actor_after, "relentless_endurance")
        and can_spend_actor_resource(actor_after, "relentless_endurance_uses")
    ):
        actor_after = spend_actor_resource(
            replace(actor_after, hp=1, death_saves=DeathSaveState()),
            "relentless_endurance_uses",
        ).actor_after
        hp = 1
        death_saves = actor_after.death_saves
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
