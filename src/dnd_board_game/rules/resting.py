from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Callable

from dnd_board_game.actors import Actor, ActorResourcePool, DeathSaveState, HitDicePool, RecoveryPeriod

from .abilities import ability_modifier

if TYPE_CHECKING:
    from dnd_board_game.inventory import ItemChargeRecoveryResult


class RestType(StrEnum):
    SHORT_REST = "short_rest"
    LONG_REST = "long_rest"


@dataclass(frozen=True, slots=True)
class RestResult:
    actor_before: Actor
    actor_after: Actor
    rest_type: RestType
    recovered_resource_ids: tuple[str, ...]
    hp_recovered: int = 0
    hit_dice_recovered: int = 0
    item_charge_recoveries: tuple[ItemChargeRecoveryResult, ...] = ()


@dataclass(frozen=True, slots=True)
class HitDieSpendResult:
    actor_before: Actor
    actor_after: Actor
    die_sides: int
    natural_roll: int
    constitution_modifier: int
    healing_total: int
    effective_healing: int


def complete_short_rest(
    actor: Actor,
    *,
    roll_die: Callable[[int], int] | None = None,
) -> RestResult:
    from dnd_board_game.inventory import ItemChargeRecovery, recover_item_charges

    resources, recovered = _recover_resources(actor, RestType.SHORT_REST)
    charges = recover_item_charges(
        actor,
        ItemChargeRecovery.SHORT_REST,
        roll_die=roll_die,
    )
    updated = replace(
        actor,
        resource_pools=resources,
        inventory=charges.actor.inventory,
    )
    return RestResult(
        actor,
        updated,
        RestType.SHORT_REST,
        recovered,
        item_charge_recoveries=charges.recoveries,
    )


def complete_long_rest(
    actor: Actor,
    *,
    roll_die: Callable[[int], int] | None = None,
) -> RestResult:
    from dnd_board_game.inventory import ItemChargeRecovery, recover_item_charges

    if actor.hp <= 0:
        raise ValueError(f"{actor.name} musi mieć co najmniej 1 HP na początku long resta.")
    resources, recovered = _recover_resources(actor, RestType.LONG_REST)
    charges = recover_item_charges(
        actor,
        ItemChargeRecovery.LONG_REST,
        roll_die=roll_die,
    )
    hit_dice, recovered_hit_dice = _recover_long_rest_hit_dice(actor)
    slots = tuple(replace(slot, remaining=slot.maximum) for slot in actor.spell_slots)
    preparation = actor.spell_preparation
    if preparation is not None:
        preparation = replace(preparation, confirmed=False)
    updated = replace(
        actor,
        hp=actor.max_hp,
        temp_hp=0,
        spell_slots=slots,
        spell_preparation=preparation,
        hit_dice=hit_dice,
        resource_pools=resources,
        inventory=charges.actor.inventory,
        death_saves=DeathSaveState(),
    )
    return RestResult(
        actor,
        updated,
        RestType.LONG_REST,
        recovered,
        hp_recovered=max(0, actor.max_hp - actor.hp),
        hit_dice_recovered=recovered_hit_dice,
        item_charge_recoveries=charges.recoveries,
    )


def spend_hit_die(actor: Actor, *, die_sides: int, natural_roll: int) -> HitDieSpendResult:
    if not 1 <= natural_roll <= die_sides:
        raise ValueError(f"Wynik d{die_sides} musi być w zakresie 1-{die_sides}.")
    pools = list(actor.hit_dice)
    pool_index = next(
        (
            index
            for index, pool in enumerate(pools)
            if pool.die_sides == die_sides and pool.remaining > 0
        ),
        None,
    )
    if pool_index is None:
        raise ValueError(f"{actor.name} nie ma dostępnej Hit Die d{die_sides}.")
    modifier = ability_modifier(actor.ability_scores.constitution)
    healing_total = max(0, natural_roll + modifier)
    hp_after = min(actor.max_hp, actor.hp + healing_total)
    pools[pool_index] = replace(pools[pool_index], remaining=pools[pool_index].remaining - 1)
    updated = replace(
        actor,
        hp=hp_after,
        hit_dice=tuple(pools),
        death_saves=DeathSaveState() if hp_after > 0 else actor.death_saves,
    )
    return HitDieSpendResult(
        actor,
        updated,
        die_sides,
        natural_roll,
        modifier,
        healing_total,
        hp_after - actor.hp,
    )


def _recover_resources(
    actor: Actor,
    rest_type: RestType,
) -> tuple[tuple[ActorResourcePool, ...], tuple[str, ...]]:
    recovered: list[str] = []
    pools = []
    for pool in actor.resource_pools:
        recovers = pool.recovery == RecoveryPeriod.SHORT_REST or (
            rest_type == RestType.LONG_REST and pool.recovery == RecoveryPeriod.LONG_REST
        )
        if recovers and pool.current < pool.maximum:
            pools.append(replace(pool, current=pool.maximum))
            recovered.append(pool.id)
        else:
            pools.append(pool)
    return tuple(pools), tuple(recovered)


def _recover_long_rest_hit_dice(actor: Actor) -> tuple[tuple[HitDicePool, ...], int]:
    if not actor.hit_dice:
        return (), 0
    recovery_budget = max(1, sum(pool.maximum for pool in actor.hit_dice) // 2)
    pools = []
    recovered = 0
    for pool in actor.hit_dice:
        amount = min(pool.maximum - pool.remaining, recovery_budget - recovered)
        pools.append(replace(pool, remaining=pool.remaining + amount))
        recovered += amount
    return tuple(pools), recovered
