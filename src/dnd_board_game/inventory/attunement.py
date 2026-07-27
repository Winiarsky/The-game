"""D&D 5e 2014 magic-item attunement rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor

    from . import InventoryItem


MAX_ATTUNED_ITEMS = 3


class ItemAttunementAction(StrEnum):
    ATTUNE = "attune"
    UNATTUNE = "unattune"


@dataclass(frozen=True, slots=True)
class ItemAttunementChoice:
    actor_id: str
    item_id: str
    action: ItemAttunementAction


@dataclass(frozen=True, slots=True)
class ItemAttunementResult:
    actor: Actor
    item: InventoryItem
    action: ItemAttunementAction


def item_power_available(item: InventoryItem) -> bool:
    """Return whether an item's magical/mechanical powers may be used."""

    return item.available and (not item.requires_attunement or item.attuned)


def attuned_item_count(actor: Actor) -> int:
    return sum(
        1
        for item in actor.inventory
        if item.requires_attunement and item.attuned
    )


def validate_attunement_limit(items: Iterable[InventoryItem]) -> None:
    count = sum(
        1
        for item in items
        if item.requires_attunement and item.attuned
    )
    if count > MAX_ATTUNED_ITEMS:
        raise ValueError(
            f"Bohater może być dostrojony najwyżej do {MAX_ATTUNED_ITEMS} przedmiotów."
        )


def apply_item_attunement(
    actor: Actor,
    *,
    item_id: str,
    action: ItemAttunementAction,
) -> ItemAttunementResult:
    item = next((candidate for candidate in actor.inventory if candidate.id == item_id), None)
    if item is None:
        raise ValueError("Bohater nie posiada wybranego przedmiotu.")
    if not item.requires_attunement:
        raise ValueError("Ten przedmiot nie wymaga dostrojenia.")
    if action == ItemAttunementAction.ATTUNE:
        if item.attuned:
            raise ValueError("Bohater jest już dostrojony do tego przedmiotu.")
        if not item.available:
            raise ValueError("Uszkodzony albo niedostępny przedmiot nie może zostać dostrojony.")
        if attuned_item_count(actor) >= MAX_ATTUNED_ITEMS:
            raise ValueError(
                f"Bohater może być dostrojony najwyżej do {MAX_ATTUNED_ITEMS} przedmiotów."
            )
        updated_item = replace(item, attuned=True)
    else:
        if not item.attuned:
            raise ValueError("Bohater nie jest dostrojony do tego przedmiotu.")
        updated_item = replace(item, attuned=False)
    updated_actor = replace(
        actor,
        inventory=tuple(
            updated_item if candidate.id == item.id else candidate
            for candidate in actor.inventory
        ),
    )
    return ItemAttunementResult(updated_actor, updated_item, action)


__all__ = [
    "MAX_ATTUNED_ITEMS",
    "ItemAttunementAction",
    "ItemAttunementChoice",
    "ItemAttunementResult",
    "apply_item_attunement",
    "attuned_item_count",
    "item_power_available",
    "validate_attunement_limit",
]
