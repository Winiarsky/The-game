from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Actor


class RecoveryPeriod(StrEnum):
    SHORT_REST = "short_rest"
    LONG_REST = "long_rest"
    NEVER = "never"


def uses_shared_mana(actor: Actor) -> bool:
    return any(f.feature_id == "shared_mana_v03" for f in actor.features)


@dataclass(frozen=True, slots=True)
class ResourceRechargeRule:
    die_sides: int = 6
    minimum_roll: int = 5

    def __post_init__(self) -> None:
        if self.die_sides < 2:
            raise ValueError("Resource recharge die must have at least two sides.")
        if not 1 <= self.minimum_roll <= self.die_sides:
            raise ValueError("Resource recharge minimum roll must fit the recharge die.")


@dataclass(frozen=True, slots=True)
class ActorResourcePool:
    id: str
    label: str
    current: int
    maximum: int
    recovery: RecoveryPeriod
    recharge: ResourceRechargeRule | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Actor resource id cannot be empty.")
        if not self.label.strip():
            raise ValueError("Actor resource label cannot be empty.")
        if self.maximum < 1:
            raise ValueError("Actor resource maximum must be positive.")
        if not 0 <= self.current <= self.maximum:
            raise ValueError("Actor resource current value must be between zero and maximum.")


@dataclass(frozen=True, slots=True)
class ActorResourceUseResult:
    actor_before: Actor
    actor_after: Actor
    resource_id: str
    cost: int


@dataclass(frozen=True, slots=True)
class ActorResourceRechargeResult:
    actor_before: Actor
    actor_after: Actor
    resource_id: str
    natural_roll: int
    recharged: bool


def actor_resource_pool(actor: Actor, resource_id: str) -> ActorResourcePool | None:
    return next(
        (pool for pool in getattr(actor, "resource_pools", ()) if pool.id == resource_id),
        None,
    )


def can_spend_actor_resource(actor: Actor, resource_id: str, cost: int = 1) -> bool:
    if physically_managed_resource(actor, resource_id):
        return cost > 0
    pool = actor_resource_pool(actor, resource_id)
    return cost > 0 and pool is not None and pool.current >= cost


def spend_actor_resource(
    actor: Actor,
    resource_id: str,
    cost: int = 1,
) -> ActorResourceUseResult:
    if cost < 1:
        raise ValueError("Actor resource cost must be positive.")
    if physically_managed_resource(actor, resource_id):
        return ActorResourceUseResult(actor, actor, resource_id, cost)
    pools = tuple(getattr(actor, "resource_pools", ()))
    pool = actor_resource_pool(actor, resource_id)
    if pool is None:
        raise ValueError(f"Nieznany zasób aktora: {resource_id}.")
    if pool.current < cost:
        raise ValueError(f"Brak użyć: {pool.label} ({pool.current}/{pool.maximum}).")
    updated_pool = replace(pool, current=pool.current - cost)
    updated_actor = replace(
        actor,
        resource_pools=tuple(updated_pool if item.id == resource_id else item for item in pools),
    )
    return ActorResourceUseResult(actor, updated_actor, resource_id, cost)


PHYSICAL_MANA_RESOURCES = frozenset({
    "tactics_uses", "rogue_tricks", "trick_uses", "instinct", "ferocity_uses", "rage_uses",
    "second_wind_uses", "action_surge_uses", "channel_divinity_uses",
    "bardic_inspiration_uses", "nimra_metamagic_points", "metamagic_points",
})


def uses_physical_mana(actor: object) -> bool:
    return any(feature.feature_id == "physical_mana_v02"
               for feature in getattr(actor, "features", ()))


def physically_managed_resource(actor: object, resource_id: str) -> bool:
    return uses_physical_mana(actor) and resource_id in PHYSICAL_MANA_RESOURCES


def depleted_recharge_resource_ids(actor: Actor) -> tuple[str, ...]:
    return tuple(
        pool.id
        for pool in getattr(actor, "resource_pools", ())
        if pool.recharge is not None and pool.current < pool.maximum
    )


def resolve_actor_resource_recharge(
    actor: Actor,
    resource_id: str,
    natural_roll: int,
) -> ActorResourceRechargeResult:
    pools = tuple(getattr(actor, "resource_pools", ()))
    pool = actor_resource_pool(actor, resource_id)
    if pool is None:
        raise ValueError(f"Nieznany zasób aktora: {resource_id}.")
    if pool.recharge is None:
        raise ValueError(f"Zasób {pool.label} nie ma reguły recharge.")
    if not 1 <= natural_roll <= pool.recharge.die_sides:
        raise ValueError(
            f"Wynik recharge d{pool.recharge.die_sides} musi być w zakresie "
            f"1-{pool.recharge.die_sides}."
        )
    recharged = natural_roll >= pool.recharge.minimum_roll and pool.current < pool.maximum
    updated_pool = replace(pool, current=pool.maximum) if recharged else pool
    updated_actor = replace(
        actor,
        resource_pools=tuple(updated_pool if item.id == resource_id else item for item in pools),
    )
    return ActorResourceRechargeResult(
        actor,
        updated_actor,
        resource_id,
        natural_roll,
        recharged,
    )


@dataclass(frozen=True, slots=True)
class HitDicePool:
    die_sides: int
    remaining: int
    maximum: int

    def __post_init__(self) -> None:
        if self.die_sides not in {6, 8, 10, 12}:
            raise ValueError("Hit Die must be d6, d8, d10, or d12.")
        if self.maximum < 1:
            raise ValueError("Hit Dice maximum must be positive.")
        if not 0 <= self.remaining <= self.maximum:
            raise ValueError("Hit Dice remaining value must be between zero and maximum.")
