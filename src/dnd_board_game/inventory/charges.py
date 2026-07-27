"""Deterministic item-charge spending and rest recovery."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Callable

from .catalog import ItemChargeRecovery

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor

    from . import InventoryItem


@dataclass(frozen=True, slots=True)
class ItemChargeSpendResult:
    actor: Actor
    item: InventoryItem
    spent: int


@dataclass(frozen=True, slots=True)
class ItemChargeRecoveryResult:
    item_id: str
    before: int
    after: int
    recovered: int
    rolls: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ItemChargeRecoveryBatch:
    actor: Actor
    recoveries: tuple[ItemChargeRecoveryResult, ...]


def has_item_use(actor: Actor, item_id: str, *, charge_cost: int = 0) -> bool:
    from .attunement import item_power_available

    item = next((candidate for candidate in actor.inventory if candidate.id == item_id), None)
    if item is None or not item_power_available(item):
        return False
    if charge_cost < 0:
        raise ValueError("Charge cost cannot be negative.")
    if charge_cost == 0:
        return item.quantity > 0
    return (
        item.charges_maximum is not None
        and item.charges_current is not None
        and item.charges_current >= charge_cost
    )


def consume_item_use(
    actor: Actor,
    item_id: str,
    *,
    charge_cost: int = 0,
) -> ItemChargeSpendResult:
    if charge_cost < 0:
        raise ValueError("Charge cost cannot be negative.")
    if charge_cost == 0:
        from . import consume_inventory_item, inventory_item_by_id

        updated = consume_inventory_item(actor, item_id)
        item = inventory_item_by_id(updated, item_id)
        if item is None:
            raise ValueError(f"Actor does not have inventory item: {item_id}.")
        return ItemChargeSpendResult(updated, item, 0)
    item = next((candidate for candidate in actor.inventory if candidate.id == item_id), None)
    if item is None or item.charges_maximum is None or item.charges_current is None:
        raise ValueError("Ten przedmiot nie korzysta z ładunków.")
    from .attunement import item_power_available

    if not item_power_available(item) or item.charges_current < charge_cost:
        raise ValueError("Przedmiot nie ma wystarczającej liczby ładunków.")
    spent_item = replace(item, charges_current=item.charges_current - charge_cost)
    updated = replace(
        actor,
        inventory=tuple(
            spent_item if candidate.id == item_id else candidate
            for candidate in actor.inventory
        ),
    )
    return ItemChargeSpendResult(updated, spent_item, charge_cost)


def recover_item_charges(
    actor: Actor,
    recovery: ItemChargeRecovery,
    *,
    roll_die: Callable[[int], int] | None = None,
) -> ItemChargeRecoveryBatch:
    if recovery == ItemChargeRecovery.NEVER:
        return ItemChargeRecoveryBatch(actor, ())
    updated_items: list[InventoryItem] = []
    results: list[ItemChargeRecoveryResult] = []
    for item in actor.inventory:
        if not _recovers_on(item.charges_recovery, recovery):
            updated_items.append(item)
            continue
        maximum = item.charges_maximum
        current = item.charges_current
        if maximum is None or current is None or current >= maximum:
            updated_items.append(item)
            continue
        rolls: tuple[int, ...] = ()
        if item.charges_recovery_dice is None:
            amount = maximum - current
        else:
            if roll_die is None:
                raise ValueError(
                    f"Odnowienie ładunków przedmiotu {item.name} wymaga źródła rzutu."
                )
            from dnd_board_game.rules import DiceExpression

            expression = DiceExpression.parse(item.charges_recovery_dice)
            rolls = expression.roll(roll_die)
            amount = max(0, sum(rolls) + item.charges_recovery_modifier)
        after = min(maximum, current + amount)
        recovered_item = replace(item, charges_current=after)
        updated_items.append(recovered_item)
        results.append(
            ItemChargeRecoveryResult(
                item_id=item.id,
                before=current,
                after=after,
                recovered=after - current,
                rolls=rolls,
            )
        )
    return ItemChargeRecoveryBatch(
        replace(actor, inventory=tuple(updated_items)),
        tuple(results),
    )


def _recovers_on(
    item_recovery: ItemChargeRecovery,
    completed_recovery: ItemChargeRecovery,
) -> bool:
    return item_recovery == completed_recovery or (
        completed_recovery == ItemChargeRecovery.LONG_REST
        and item_recovery == ItemChargeRecovery.SHORT_REST
    )


__all__ = [
    "ItemChargeRecoveryBatch",
    "ItemChargeRecoveryResult",
    "ItemChargeSpendResult",
    "consume_item_use",
    "has_item_use",
    "recover_item_charges",
]
