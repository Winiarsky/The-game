"""Items, equipment, and inventory rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor


@dataclass(frozen=True, slots=True)
class InventoryItem:
    id: str
    name: str
    kind: str
    quantity: int = 1
    equipped: bool = True
    source_ref: str | None = None
    broken: bool = False

    @property
    def available(self) -> bool:
        return self.quantity > 0 and not self.broken


def inventory_item_payload(item: InventoryItem) -> dict[str, object]:
    return {
        "id": item.id,
        "name": item.name,
        "kind": item.kind,
        "quantity": item.quantity,
        "equipped": item.equipped,
        "source_ref": item.source_ref,
        "broken": item.broken,
        "available": item.available,
    }


def inventory_item_by_id(actor: Actor, item_id: str) -> InventoryItem | None:
    return next((item for item in actor.inventory if item.id == item_id), None)


def has_inventory_quantity(actor: Actor, item_id: str, quantity: int = 1) -> bool:
    item = inventory_item_by_id(actor, item_id)
    return item is not None and item.quantity >= quantity and not item.broken


def consume_inventory_item(actor: Actor, item_id: str, quantity: int = 1) -> Actor:
    if quantity <= 0:
        raise ValueError("Consumed inventory quantity must be positive.")
    items = list(actor.inventory)
    for index, item in enumerate(items):
        if item.id != item_id:
            continue
        if item.quantity < quantity:
            raise ValueError(f"Not enough inventory quantity for item: {item_id}.")
        items[index] = replace(item, quantity=item.quantity - quantity)
        return replace(actor, inventory=tuple(items))
    raise ValueError(f"Actor does not have inventory item: {item_id}.")


def break_inventory_item(actor: Actor, item_id: str) -> Actor:
    items = list(actor.inventory)
    for index, item in enumerate(items):
        if item.id != item_id:
            continue
        items[index] = replace(item, broken=True)
        return replace(actor, inventory=tuple(items))
    raise ValueError(f"Actor does not have inventory item: {item_id}.")


__all__ = [
    "InventoryItem",
    "break_inventory_item",
    "consume_inventory_item",
    "has_inventory_quantity",
    "inventory_item_by_id",
    "inventory_item_payload",
]
