"""Items, equipment, and inventory rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .catalog import (
    ItemCollectionDestination,
    ItemDefinition,
    ItemInstance,
    ItemPropertyCatalog,
    ItemPropertyDefinition,
)
from .armor import effective_armor_class, equipped_armor_class_bonus
from .hands import (
    HAND_SLOTS,
    HandEquipPlan,
    HandLoadout,
    HandSlot,
    free_hand_count,
    hand_loadout,
    hand_loadout_payload,
    hands_required,
    normalize_hand_equipment,
    plan_hand_equip,
)

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
    description: str = ""
    properties: tuple[str, ...] = ()
    portable: bool = True
    hands_required: int = 0
    held_in: tuple[HandSlot, ...] = ()
    light_weapon: bool = False
    versatile_damage_dice: str | None = None
    armor_class_bonus: int = 0
    armor_proficiency: str | None = None

    def __post_init__(self) -> None:
        if self.hands_required not in {0, 1, 2}:
            raise ValueError("hands_required must be 0, 1, or 2.")
        if len(self.held_in) != len(set(self.held_in)):
            raise ValueError("held_in cannot contain duplicate hand slots.")
        if any(slot not in HAND_SLOTS for slot in self.held_in):
            raise ValueError("held_in contains an unknown hand slot.")
        if self.held_in and not self.equipped:
            raise ValueError("An unequipped item cannot occupy a hand slot.")
        if self.armor_class_bonus < 0:
            raise ValueError("armor_class_bonus cannot be negative.")

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
        "description": item.description,
        "properties": list(item.properties),
        "portable": item.portable,
        "hands_required": hands_required(item),
        "held_in": [slot.value for slot in item.held_in],
        "light_weapon": item.light_weapon,
        "versatile_damage_dice": item.versatile_damage_dice,
        "armor_class_bonus": item.armor_class_bonus,
        "armor_proficiency": item.armor_proficiency,
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


def add_inventory_item(actor: Actor, item: InventoryItem) -> Actor:
    """Add an item instance or merge another quantity of the same instance."""

    if item.quantity <= 0:
        raise ValueError("Added inventory quantity must be positive.")
    items = list(actor.inventory)
    for index, current in enumerate(items):
        if current.id != item.id:
            continue
        if (
            current.name,
            current.kind,
            current.source_ref,
            current.properties,
            current.portable,
            current.hands_required,
            current.light_weapon,
            current.versatile_damage_dice,
            current.armor_class_bonus,
            current.armor_proficiency,
        ) != (
            item.name,
            item.kind,
            item.source_ref,
            item.properties,
            item.portable,
            item.hands_required,
            item.light_weapon,
            item.versatile_damage_dice,
            item.armor_class_bonus,
            item.armor_proficiency,
        ):
            raise ValueError(f"Inventory item id collision: {item.id}.")
        items[index] = replace(current, quantity=current.quantity + item.quantity)
        return replace(actor, inventory=tuple(items))
    return replace(actor, inventory=(*actor.inventory, item))


def break_inventory_item(actor: Actor, item_id: str) -> Actor:
    items = list(actor.inventory)
    for index, item in enumerate(items):
        if item.id != item_id:
            continue
        items[index] = replace(item, broken=True)
        return replace(actor, inventory=tuple(items))
    raise ValueError(f"Actor does not have inventory item: {item_id}.")


__all__ = [
    "ItemDefinition",
    "ItemCollectionDestination",
    "ItemInstance",
    "ItemPropertyCatalog",
    "ItemPropertyDefinition",
    "InventoryItem",
    "HAND_SLOTS",
    "HandEquipPlan",
    "HandLoadout",
    "HandSlot",
    "add_inventory_item",
    "break_inventory_item",
    "consume_inventory_item",
    "effective_armor_class",
    "equipped_armor_class_bonus",
    "has_inventory_quantity",
    "inventory_item_by_id",
    "inventory_item_payload",
    "free_hand_count",
    "hand_loadout",
    "hand_loadout_payload",
    "hands_required",
    "normalize_hand_equipment",
    "plan_hand_equip",
]
