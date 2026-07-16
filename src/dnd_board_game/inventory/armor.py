"""Deterministic armor-class effects provided by equipped inventory."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from dnd_board_game.actors import Actor

    from . import InventoryItem


def equipped_armor_class_bonus(items: Sequence[InventoryItem]) -> int:
    active = tuple(
        item
        for item in items
        if item.available
        and item.equipped
        and item.armor_class_bonus > 0
        and (item.kind != "shield" or len(item.held_in) == 1)
    )
    shield_bonus = max(
        (item.armor_class_bonus for item in active if item.kind == "shield"),
        default=0,
    )
    return shield_bonus + sum(
        item.armor_class_bonus for item in active if item.kind != "shield"
    )


def effective_armor_class(actor: Actor) -> int:
    return actor.ac + equipped_armor_class_bonus(actor.inventory)


__all__ = ["effective_armor_class", "equipped_armor_class_bonus"]
