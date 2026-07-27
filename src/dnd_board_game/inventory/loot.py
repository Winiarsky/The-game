"""Generic loot bundles reusable by defeated actors, corpses, and containers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .economy import CurrencyWallet, carried_weight_lb, carrying_capacity_lb

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor
    from dnd_board_game.inventory import InventoryItem


@dataclass(frozen=True, slots=True)
class LootBundle:
    id: str
    label: str
    items: tuple[InventoryItem, ...] = ()
    currency: CurrencyWallet = CurrencyWallet()

    @property
    def is_empty(self) -> bool:
        return not self.items and self.currency.is_empty


@dataclass(frozen=True, slots=True)
class LootTransferResult:
    source: Actor
    recipient: Actor
    items: tuple[InventoryItem, ...]
    currency: CurrencyWallet


@dataclass(frozen=True, slots=True)
class LootBundleTransferResult:
    bundle: LootBundle
    recipient: Actor
    items: tuple[InventoryItem, ...]
    currency: CurrencyWallet


def loot_bundle_from_actor(
    actor: Actor,
    *,
    excluded_item_ids: frozenset[str] = frozenset(),
) -> LootBundle:
    items = tuple(
        replace(item, equipped=False, held_in=())
        for item in actor.inventory
        if item.available
        and item.portable
        and not item.equipped
        and item.id not in excluded_item_ids
    )
    return LootBundle(
        id=f"actor:{actor.id}",
        label=actor.name,
        items=items,
        currency=actor.currency,
    )


def transfer_all_actor_loot(
    source: Actor,
    recipient: Actor,
    *,
    excluded_item_ids: frozenset[str] = frozenset(),
) -> LootTransferResult:
    """Atomically move all available loot from one actor to another."""

    bundle = loot_bundle_from_actor(source, excluded_item_ids=excluded_item_ids)
    transfer = transfer_all_loot(bundle, recipient)

    transferred_ids = {item.id for item in bundle.items}
    updated_source = replace(
        source,
        inventory=tuple(item for item in source.inventory if item.id not in transferred_ids),
        currency=CurrencyWallet(),
    )
    return LootTransferResult(
        source=updated_source,
        recipient=transfer.recipient,
        items=transfer.items,
        currency=transfer.currency,
    )


def transfer_actor_loot(
    source: Actor,
    recipient: Actor,
    *,
    item_id: str | None = None,
    quantity: int | None = None,
    currency: CurrencyWallet = CurrencyWallet(),
    excluded_item_ids: frozenset[str] = frozenset(),
) -> LootTransferResult:
    """Move one item stack, part of a stack, currency, or both from an actor."""

    bundle = loot_bundle_from_actor(source, excluded_item_ids=excluded_item_ids)
    transfer = transfer_loot(
        bundle,
        recipient,
        item_id=item_id,
        quantity=quantity,
        currency=currency,
    )
    eligible_ids = {item.id for item in bundle.items}
    remaining_by_id = {item.id: item for item in transfer.bundle.items}
    updated_inventory = []
    for item in source.inventory:
        if item.id not in eligible_ids:
            updated_inventory.append(item)
            continue
        remaining = remaining_by_id.get(item.id)
        if remaining is not None:
            updated_inventory.append(replace(item, quantity=remaining.quantity))
    return LootTransferResult(
        source=replace(
            source,
            inventory=tuple(updated_inventory),
            currency=transfer.bundle.currency,
        ),
        recipient=transfer.recipient,
        items=transfer.items,
        currency=transfer.currency,
    )


def transfer_all_loot(bundle: LootBundle, recipient: Actor) -> LootBundleTransferResult:
    """Atomically empty a generic corpse/container bundle into an actor inventory."""

    from dnd_board_game.inventory import add_inventory_item

    if bundle.is_empty:
        raise ValueError("Źródło łupu jest puste.")
    updated_recipient = recipient
    for item in bundle.items:
        updated_recipient = add_inventory_item(updated_recipient, item)
    updated_recipient = replace(
        updated_recipient,
        currency=updated_recipient.currency.add(bundle.currency),
    )
    if carried_weight_lb(updated_recipient) > carrying_capacity_lb(updated_recipient):
        raise ValueError(
            "Cały łup przekracza udźwig postaci "
            f"({carried_weight_lb(updated_recipient):g}/{carrying_capacity_lb(updated_recipient):g} lb)."
        )
    return LootBundleTransferResult(
        bundle=replace(bundle, items=(), currency=CurrencyWallet()),
        recipient=updated_recipient,
        items=bundle.items,
        currency=bundle.currency,
    )


def transfer_loot(
    bundle: LootBundle,
    recipient: Actor,
    *,
    item_id: str | None = None,
    quantity: int | None = None,
    currency: CurrencyWallet = CurrencyWallet(),
) -> LootBundleTransferResult:
    """Atomically transfer a selected part of a generic loot bundle."""

    from dnd_board_game.inventory import add_inventory_item

    if item_id is None and quantity is not None:
        raise ValueError("Liczbę sztuk można podać tylko dla wybranego przedmiotu.")
    if item_id is None and currency.is_empty:
        raise ValueError("Nie wybrano żadnego łupu.")

    transferred_items: tuple[InventoryItem, ...] = ()
    remaining_items = list(bundle.items)
    updated_recipient = recipient
    if item_id is not None:
        selected = next((item for item in bundle.items if item.id == item_id), None)
        if selected is None:
            raise ValueError("Wybrany przedmiot nie jest już dostępny w łupie.")
        selected_quantity = selected.quantity if quantity is None else quantity
        if selected_quantity < 1:
            raise ValueError("Liczba zabieranych przedmiotów musi być dodatnia.")
        if selected_quantity > selected.quantity:
            raise ValueError(
                f"Dostępna liczba przedmiotu {selected.name}: {selected.quantity}."
            )
        transferred_item = replace(selected, quantity=selected_quantity)
        transferred_items = (transferred_item,)
        updated_recipient = add_inventory_item(updated_recipient, transferred_item)
        remaining_items = [
            (
                replace(item, quantity=item.quantity - selected_quantity)
                if item.id == item_id and item.quantity > selected_quantity
                else item
            )
            for item in remaining_items
            if item.id != item_id or item.quantity > selected_quantity
        ]

    remaining_currency = bundle.currency.subtract(currency)
    updated_recipient = replace(
        updated_recipient,
        currency=updated_recipient.currency.add(currency),
    )
    if carried_weight_lb(updated_recipient) > carrying_capacity_lb(updated_recipient):
        raise ValueError(
            "Wybrany łup przekracza udźwig postaci "
            f"({carried_weight_lb(updated_recipient):g}/{carrying_capacity_lb(updated_recipient):g} lb)."
        )
    return LootBundleTransferResult(
        bundle=replace(
            bundle,
            items=tuple(remaining_items),
            currency=remaining_currency,
        ),
        recipient=updated_recipient,
        items=transferred_items,
        currency=currency,
    )
