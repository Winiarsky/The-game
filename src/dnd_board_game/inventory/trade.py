"""Deterministic merchant stock and item trade."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from .economy import (
    CurrencyWallet,
    carried_weight_lb,
    carrying_capacity_lb,
    currency_wallet_from_cp,
)

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor
    from dnd_board_game.inventory import InventoryItem


@dataclass(frozen=True, slots=True)
class MerchantState:
    id: str
    name: str
    inventory: tuple[InventoryItem, ...] = ()
    currency: CurrencyWallet = CurrencyWallet()
    buyback_percent: int = 50

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Merchant requires a stable id and name.")
        if not 0 <= self.buyback_percent <= 100:
            raise ValueError("Merchant buyback_percent must be between 0 and 100.")
        item_ids = tuple(item.id for item in self.inventory)
        if len(item_ids) != len(set(item_ids)):
            raise ValueError("Merchant inventory item ids must be unique.")
        if any(item.equipped for item in self.inventory):
            raise ValueError("Merchant stock cannot contain equipped items.")


@dataclass(frozen=True, slots=True)
class TradeResult:
    merchant: MerchantState
    actor: Actor
    item: InventoryItem
    quantity: int
    total_cp: int


def merchant_item(merchant: MerchantState, item_id: str) -> InventoryItem | None:
    return next(
        (
            item
            for item in merchant.inventory
            if item.id == item_id and item.available
        ),
        None,
    )


def merchant_sell_unit_price_cp(item: InventoryItem) -> int:
    if item.value_cp <= 0:
        raise ValueError(f"Przedmiot {item.name} nie ma ceny sprzedaży.")
    return item.value_cp


def merchant_buy_unit_price_cp(
    merchant: MerchantState,
    item: InventoryItem,
) -> int:
    if item.value_cp <= 0:
        raise ValueError(f"Przedmiot {item.name} nie ma wartości odkupu.")
    price = item.value_cp * merchant.buyback_percent // 100
    if price <= 0:
        raise ValueError(f"Przedmiot {item.name} ma zbyt małą wartość do odkupienia.")
    return price


def buy_from_merchant(
    merchant: MerchantState,
    actor: Actor,
    *,
    item_id: str,
    quantity: int,
) -> TradeResult:
    """Buy stock at catalog value and normalize both wallets as change."""

    from dnd_board_game.inventory import add_inventory_item

    if quantity < 1:
        raise ValueError("Liczba kupowanych sztuk musi być dodatnia.")
    stock = merchant_item(merchant, item_id)
    if stock is None:
        raise ValueError("Wybrany przedmiot nie jest dostępny u sprzedawcy.")
    if quantity > stock.quantity:
        raise ValueError(f"Sprzedawca ma tylko {stock.quantity} szt. przedmiotu {stock.name}.")
    unit_price = merchant_sell_unit_price_cp(stock)
    total_cp = unit_price * quantity
    if actor.currency.total_cp < total_cp:
        raise ValueError(
            f"{actor.name} nie ma dość monet: potrzeba {total_cp} cp, "
            f"dostępne {actor.currency.total_cp} cp."
        )
    purchased = replace(stock, quantity=quantity, equipped=False, held_in=())
    updated_actor = add_inventory_item(actor, purchased)
    updated_actor = replace(
        updated_actor,
        currency=currency_wallet_from_cp(actor.currency.total_cp - total_cp),
    )
    if carried_weight_lb(updated_actor) > carrying_capacity_lb(updated_actor):
        raise ValueError(
            "Zakup przekracza udźwig postaci "
            f"({carried_weight_lb(updated_actor):g}/{carrying_capacity_lb(updated_actor):g} lb)."
        )
    remaining_stock = tuple(
        replace(item, quantity=item.quantity - quantity)
        if item.id == item_id and item.quantity > quantity
        else item
        for item in merchant.inventory
        if item.id != item_id or item.quantity > quantity
    )
    updated_merchant = replace(
        merchant,
        inventory=remaining_stock,
        currency=currency_wallet_from_cp(merchant.currency.total_cp + total_cp),
    )
    return TradeResult(updated_merchant, updated_actor, purchased, quantity, total_cp)


def sell_to_merchant(
    merchant: MerchantState,
    actor: Actor,
    *,
    item_id: str,
    quantity: int,
) -> TradeResult:
    """Sell an unequipped portable stack at the merchant buyback rate."""

    from dnd_board_game.inventory import add_inventory_item

    if quantity < 1:
        raise ValueError("Liczba sprzedawanych sztuk musi być dodatnia.")
    item = next(
        (
            candidate
            for candidate in actor.inventory
            if candidate.id == item_id
            and candidate.available
            and candidate.portable
            and not candidate.equipped
        ),
        None,
    )
    if item is None:
        raise ValueError("Wybrany przedmiot nie może zostać sprzedany.")
    if quantity > item.quantity:
        raise ValueError(f"Postać ma tylko {item.quantity} szt. przedmiotu {item.name}.")
    unit_price = merchant_buy_unit_price_cp(merchant, item)
    total_cp = unit_price * quantity
    if merchant.currency.total_cp < total_cp:
        raise ValueError(
            f"{merchant.name} nie ma dość monet: potrzeba {total_cp} cp, "
            f"dostępne {merchant.currency.total_cp} cp."
        )
    sold = replace(item, quantity=quantity, equipped=False, held_in=())
    merchant_actor_proxy = _MerchantInventoryProxy(merchant.inventory)
    merchant_inventory = add_inventory_item(merchant_actor_proxy, sold).inventory
    actor_inventory = tuple(
        replace(candidate, quantity=candidate.quantity - quantity)
        if candidate.id == item_id and candidate.quantity > quantity
        else candidate
        for candidate in actor.inventory
        if candidate.id != item_id or candidate.quantity > quantity
    )
    updated_actor = replace(
        actor,
        inventory=actor_inventory,
        currency=currency_wallet_from_cp(actor.currency.total_cp + total_cp),
    )
    updated_merchant = replace(
        merchant,
        inventory=merchant_inventory,
        currency=currency_wallet_from_cp(merchant.currency.total_cp - total_cp),
    )
    return TradeResult(updated_merchant, updated_actor, sold, quantity, total_cp)


@dataclass(frozen=True, slots=True)
class _MerchantInventoryProxy:
    inventory: tuple[InventoryItem, ...]
