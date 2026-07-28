from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Callable

from dnd_board_game.actors import (
    Actor,
    ActorResourcePool,
    DeathSaveState,
    HitDicePool,
    RecoveryPeriod,
    actor_has_feature,
    can_spend_actor_resource,
    spend_actor_resource,
)

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


@dataclass(frozen=True, slots=True)
class ArcaneRecoveryResult:
    rest_before: RestResult
    rest_after: RestResult
    actor_before: Actor
    actor_after: Actor
    slot_level: int


def apply_short_rest_slot_recovery(
    actor: Actor,
    *,
    slot_levels: tuple[int, ...],
) -> Actor:
    """Apply Arcane or Natural Recovery once after a completed short rest."""
    if actor_has_feature(actor, "arcane_recovery"):
        resource_id = "arcane_recovery_uses"
        label = "Arcane Recovery"
    elif actor_has_feature(actor, "natural_recovery"):
        resource_id = "natural_recovery_uses"
        label = "Natural Recovery"
    else:
        raise ValueError("Postać nie posiada Arcane Recovery ani Natural Recovery.")
    if not slot_levels:
        raise ValueError(f"{label} wymaga wyboru co najmniej jednego slotu.")
    if not can_spend_actor_resource(actor, resource_id):
        raise ValueError(f"{label} zostało już wykorzystane od ostatniego long resta.")
    budget = max(1, (actor.level + 1) // 2)
    if sum(slot_levels) > budget or any(level < 1 or level >= 6 for level in slot_levels):
        raise ValueError(f"{label} przekracza budżet {budget} poziomów slotów.")
    requested: dict[int, int] = {}
    for level in slot_levels:
        requested[level] = requested.get(level, 0) + 1
    slots = list(actor.spell_slots)
    for level, count in requested.items():
        slot_index = next(
            (
                index
                for index, slot in enumerate(slots)
                if slot.level == level and not slot.temporary
            ),
            None,
        )
        if slot_index is None:
            raise ValueError(f"Postać nie posiada zwykłych slotów {level}. poziomu.")
        slot = slots[slot_index]
        if slot.remaining + count > slot.maximum:
            raise ValueError(f"Nie można odzyskać tylu slotów {level}. poziomu.")
        slots[slot_index] = replace(slot, remaining=slot.remaining + count)
    spent = spend_actor_resource(actor, resource_id)
    return replace(spent.actor_after, spell_slots=tuple(slots))


def long_rest_required_minutes(actor: Actor) -> int:
    """Return the uninterrupted rest duration required by the actor."""
    return 240 if actor_has_feature(actor, "trance") else 480


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
        spell_slots=tuple(
            replace(slot, remaining=slot.maximum)
            if slot.recovery == RestType.SHORT_REST.value
            else slot
            for slot in actor.spell_slots
        ),
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
    slots = tuple(
        replace(slot, remaining=slot.maximum)
        for slot in actor.spell_slots
        if not slot.temporary
    )
    preparation = actor.spell_preparation
    if preparation is not None:
        preparation = replace(preparation, confirmed=False)
    exhaustion_level = max(0, actor.exhaustion_level - 1)
    restored_max_hp = _effective_max_hit_points(actor, exhaustion_level)
    updated = replace(
        actor,
        hp=restored_max_hp,
        exhaustion_level=exhaustion_level,
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
        hp_recovered=max(0, restored_max_hp - actor.hp),
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
    hp_after = min(_effective_max_hit_points(actor), actor.hp + healing_total)
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


def apply_arcane_recovery(
    rest: RestResult,
    *,
    slot_level: int,
) -> ArcaneRecoveryResult:
    """Spend Arcane Recovery after a short rest and restore one legal spell slot."""
    actor = rest.actor_after
    if rest.rest_type != RestType.SHORT_REST:
        raise ValueError("Arcane Recovery można zastosować wyłącznie po short reście.")
    if not actor_has_feature(actor, "arcane_recovery"):
        raise ValueError(f"{actor.name} nie posiada cechy Arcane Recovery.")
    if not can_spend_actor_resource(actor, "arcane_recovery_uses"):
        raise ValueError("Arcane Recovery zostało już wykorzystane od ostatniego long resta.")
    recovery_budget = max(1, (actor.level + 1) // 2)
    if slot_level < 1 or slot_level > recovery_budget or slot_level >= 6:
        raise ValueError(
            f"Arcane Recovery tej postaci może odzyskać slot najwyżej {recovery_budget}. poziomu."
        )
    target = next(
        (slot for slot in actor.spell_slots if slot.level == slot_level),
        None,
    )
    if target is None:
        raise ValueError(f"{actor.name} nie posiada slotu {slot_level}. poziomu.")
    if target.remaining >= target.maximum:
        raise ValueError(f"Sloty {slot_level}. poziomu są już pełne.")
    spent = spend_actor_resource(actor, "arcane_recovery_uses")
    updated_slots = tuple(
        replace(slot, remaining=slot.remaining + 1)
        if slot.level == slot_level
        else slot
        for slot in spent.actor_after.spell_slots
    )
    updated_actor = replace(spent.actor_after, spell_slots=updated_slots)
    updated_rest = replace(rest, actor_after=updated_actor)
    return ArcaneRecoveryResult(
        rest_before=rest,
        rest_after=updated_rest,
        actor_before=actor,
        actor_after=updated_actor,
        slot_level=slot_level,
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


def _effective_max_hit_points(actor: Actor, exhaustion_level: int | None = None) -> int:
    level = actor.exhaustion_level if exhaustion_level is None else exhaustion_level
    return actor.max_hp // 2 if level >= 4 else actor.max_hp
