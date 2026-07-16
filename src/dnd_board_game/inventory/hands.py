"""Deterministic hand-slot rules for held equipment."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from . import InventoryItem


class HandSlot(StrEnum):
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"


HAND_SLOTS = (HandSlot.MAIN_HAND, HandSlot.OFF_HAND)


@dataclass(frozen=True, slots=True)
class HandLoadout:
    main_hand_item_id: str | None = None
    off_hand_item_id: str | None = None

    def item_id(self, slot: HandSlot) -> str | None:
        return self.main_hand_item_id if slot == HandSlot.MAIN_HAND else self.off_hand_item_id

    @property
    def free_slots(self) -> tuple[HandSlot, ...]:
        return tuple(slot for slot in HAND_SLOTS if self.item_id(slot) is None)


@dataclass(frozen=True, slots=True)
class HandEquipPlan:
    inventory: tuple[InventoryItem, ...]
    item_id: str
    occupied_slots: tuple[HandSlot, ...]
    replaced_item_ids: tuple[str, ...]


def hands_required(item: InventoryItem) -> int:
    """Return the held-hand requirement, retaining old weapon fixtures as one-handed."""

    if item.hands_required:
        return item.hands_required
    return 1 if item.kind == "weapon" else 0


def normalize_hand_equipment(items: Sequence[InventoryItem]) -> tuple[InventoryItem, ...]:
    """Ground legacy equipped flags into unique, explicit hand slots."""

    occupied: set[HandSlot] = set()
    normalized: list[InventoryItem] = []
    for item in items:
        required = hands_required(item)
        if required == 0:
            normalized.append(replace(item, held_in=()))
            continue
        if not item.equipped or not item.available:
            normalized.append(replace(item, equipped=False, held_in=()))
            continue

        requested = tuple(dict.fromkeys(item.held_in))
        valid_requested = (
            len(requested) == required
            and all(slot in HAND_SLOTS for slot in requested)
            and not occupied.intersection(requested)
        )
        if valid_requested:
            assigned = requested
        else:
            free = tuple(slot for slot in HAND_SLOTS if slot not in occupied)
            assigned = free[:required]
        if len(assigned) != required:
            normalized.append(replace(item, equipped=False, held_in=()))
            continue
        occupied.update(assigned)
        normalized.append(replace(item, equipped=True, held_in=assigned))
    return tuple(normalized)


def hand_loadout(items: Sequence[InventoryItem]) -> HandLoadout:
    normalized = normalize_hand_equipment(items)
    by_slot: dict[HandSlot, str] = {}
    for item in normalized:
        for slot in item.held_in:
            by_slot[slot] = item.id
    return HandLoadout(
        main_hand_item_id=by_slot.get(HandSlot.MAIN_HAND),
        off_hand_item_id=by_slot.get(HandSlot.OFF_HAND),
    )


def free_hand_count(items: Sequence[InventoryItem], *, reserved_hands: int = 0) -> int:
    return max(0, len(hand_loadout(items).free_slots) - max(0, reserved_hands))


def plan_hand_equip(
    items: Sequence[InventoryItem],
    item_id: str,
    *,
    preferred_slot: HandSlot | None = None,
) -> HandEquipPlan:
    normalized = normalize_hand_equipment(items)
    target = next((item for item in normalized if item.id == item_id), None)
    if target is None:
        raise ValueError(f"Unknown inventory item: {item_id}.")
    required = hands_required(target)
    if required not in {1, 2}:
        raise ValueError(f"Item {item_id} is not held equipment.")

    loadout = hand_loadout(normalized)
    if required == 2:
        target_slots = HAND_SLOTS
    elif preferred_slot is not None:
        target_slots = (preferred_slot,)
    elif loadout.free_slots:
        target_slots = (loadout.free_slots[0],)
    else:
        # Keep the main-hand weapon stable when both hands are occupied.
        target_slots = (HandSlot.OFF_HAND,)

    replaced_ids = tuple(
        dict.fromkeys(
            existing_id
            for slot in target_slots
            for existing_id in (loadout.item_id(slot),)
            if existing_id is not None and existing_id != item_id
        )
    )
    updated = tuple(
        replace(item, equipped=False, held_in=())
        if item.id in replaced_ids
        else replace(item, equipped=True, held_in=target_slots)
        if item.id == item_id
        else item
        for item in normalized
    )
    return HandEquipPlan(
        inventory=normalize_hand_equipment(updated),
        item_id=item_id,
        occupied_slots=target_slots,
        replaced_item_ids=replaced_ids,
    )


def hand_loadout_payload(
    items: Sequence[InventoryItem],
    *,
    reserved_hands: int = 0,
) -> dict[str, object]:
    normalized = normalize_hand_equipment(items)
    loadout = hand_loadout(normalized)
    by_id = {item.id: item for item in normalized}

    def slot_payload(slot: HandSlot) -> dict[str, object] | None:
        item_id = loadout.item_id(slot)
        if item_id is None:
            return None
        item = by_id[item_id]
        return {"item_id": item.id, "item_name": item.name}

    return {
        "main_hand": slot_payload(HandSlot.MAIN_HAND),
        "off_hand": slot_payload(HandSlot.OFF_HAND),
        "free_item_hands": len(loadout.free_slots),
        "reserved_hands": max(0, reserved_hands),
        "free_hands": free_hand_count(normalized, reserved_hands=reserved_hands),
    }


__all__ = [
    "HAND_SLOTS",
    "HandEquipPlan",
    "HandLoadout",
    "HandSlot",
    "free_hand_count",
    "hand_loadout",
    "hand_loadout_payload",
    "hands_required",
    "normalize_hand_equipment",
    "plan_hand_equip",
]
