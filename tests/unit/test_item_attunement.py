from dataclasses import replace

import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.inventory import (
    MAX_ATTUNED_ITEMS,
    InventoryItem,
    ItemAttunementAction,
    apply_item_attunement,
    attuned_item_count,
    has_item_use,
    item_power_available,
    validate_attunement_limit,
)
from dnd_board_game.world import Coordinate


def _item(item_id: str, *, attuned: bool = False) -> InventoryItem:
    return InventoryItem(
        item_id,
        item_id,
        "magic_item",
        equipped=False,
        charges_maximum=3,
        requires_attunement=True,
        attuned=attuned,
    )


def _actor(*items: InventoryItem) -> Actor:
    return Actor(
        ActorId("hero"),
        "Bohater",
        12,
        10,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        inventory=items,
    )


def test_attunement_unlocks_item_power_and_can_be_ended() -> None:
    actor = _actor(_item("wand"))

    assert not item_power_available(actor.inventory[0])
    assert not has_item_use(actor, "wand", charge_cost=1)

    attuned = apply_item_attunement(
        actor,
        item_id="wand",
        action=ItemAttunementAction.ATTUNE,
    )

    assert item_power_available(attuned.item)
    assert has_item_use(attuned.actor, "wand", charge_cost=1)
    assert attuned_item_count(attuned.actor) == 1

    ended = apply_item_attunement(
        attuned.actor,
        item_id="wand",
        action=ItemAttunementAction.UNATTUNE,
    )

    assert ended.item.attuned is False
    assert not has_item_use(ended.actor, "wand", charge_cost=1)


def test_attunement_enforces_three_item_limit() -> None:
    actor = _actor(
        *(_item(f"item_{index}", attuned=True) for index in range(MAX_ATTUNED_ITEMS)),
        _item("fourth"),
    )

    with pytest.raises(ValueError, match="najwyżej do 3"):
        apply_item_attunement(
            actor,
            item_id="fourth",
            action=ItemAttunementAction.ATTUNE,
        )
    with pytest.raises(ValueError, match="najwyżej do 3"):
        validate_attunement_limit(
            _item(f"loaded_{index}", attuned=True)
            for index in range(MAX_ATTUNED_ITEMS + 1)
        )


def test_attunement_rejects_ordinary_or_stacked_items() -> None:
    actor = _actor(InventoryItem("rope", "Lina", "tool", equipped=False))

    with pytest.raises(ValueError, match="nie wymaga dostrojenia"):
        apply_item_attunement(
            actor,
            item_id="rope",
            action=ItemAttunementAction.ATTUNE,
        )
    with pytest.raises(ValueError, match="cannot be stacked"):
        replace(_item("rings"), quantity=2)
