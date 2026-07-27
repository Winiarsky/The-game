"""Deterministic ammunition availability and consumption."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor
    from dnd_board_game.inventory import InventoryItem


@dataclass(frozen=True, slots=True)
class AmmunitionUse:
    actor_after: Actor
    ammunition_type: str
    quantity: int
    item_ids: tuple[str, ...]
    consumed_items: tuple[InventoryItem, ...]


def ammunition_quantity(actor: Actor, ammunition_type: str) -> int:
    normalized = ammunition_type.strip()
    if not normalized:
        raise ValueError("Ammunition type cannot be empty.")
    return sum(
        item.quantity
        for item in actor.inventory
        if item.ammunition_type == normalized and item.available
    )


def has_ammunition(actor: Actor, ammunition_type: str, quantity: int = 1) -> bool:
    if quantity < 1:
        raise ValueError("Required ammunition quantity must be positive.")
    return ammunition_quantity(actor, ammunition_type) >= quantity


def consume_ammunition(
    actor: Actor,
    ammunition_type: str,
    quantity: int = 1,
) -> AmmunitionUse:
    """Consume ammunition across compatible inventory stacks."""

    if quantity < 1:
        raise ValueError("Consumed ammunition quantity must be positive.")
    if not has_ammunition(actor, ammunition_type, quantity):
        raise ValueError(f"Brak amunicji typu {ammunition_type}.")
    remaining = quantity
    consumed_ids: list[str] = []
    consumed_items: list[InventoryItem] = []
    inventory = []
    for item in actor.inventory:
        if remaining <= 0 or item.ammunition_type != ammunition_type or not item.available:
            inventory.append(item)
            continue
        consumed = min(item.quantity, remaining)
        inventory.append(replace(item, quantity=item.quantity - consumed))
        remaining -= consumed
        consumed_ids.append(item.id)
        consumed_items.append(
            replace(
                item,
                quantity=consumed,
                equipped=False,
                held_in=(),
            )
        )
    return AmmunitionUse(
        actor_after=replace(actor, inventory=tuple(inventory)),
        ammunition_type=ammunition_type,
        quantity=quantity,
        item_ids=tuple(consumed_ids),
        consumed_items=tuple(consumed_items),
    )
