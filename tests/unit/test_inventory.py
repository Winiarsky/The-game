import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.inventory import InventoryItem, add_inventory_item, break_inventory_item, consume_inventory_item, has_inventory_quantity
from dnd_board_game.world import Coordinate


def _actor_with_inventory(*items: InventoryItem) -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Hero",
        ac=14,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        inventory=items,
    )


def test_consume_inventory_item_decreases_quantity_without_mutating_actor():
    actor = _actor_with_inventory(InventoryItem("strength_potion", "Napój siły", "consumable", quantity=1))

    updated = consume_inventory_item(actor, "strength_potion")

    assert has_inventory_quantity(actor, "strength_potion") is True
    assert has_inventory_quantity(updated, "strength_potion") is False
    assert updated.inventory[0].quantity == 0


def test_consume_inventory_item_rejects_missing_or_insufficient_quantity():
    actor = _actor_with_inventory(InventoryItem("strength_potion", "Napój siły", "consumable", quantity=0))

    with pytest.raises(ValueError, match="Not enough"):
        consume_inventory_item(actor, "strength_potion")
    with pytest.raises(ValueError, match="does not have"):
        consume_inventory_item(actor, "missing")


def test_broken_inventory_item_is_visible_but_unavailable():
    actor = _actor_with_inventory(InventoryItem("thieves_tools", "Narzędzia", "tool", quantity=1))

    updated = break_inventory_item(actor, "thieves_tools")

    assert updated.inventory[0].quantity == 1
    assert updated.inventory[0].broken is True
    assert updated.inventory[0].available is False
    assert has_inventory_quantity(updated, "thieves_tools") is False


def test_add_inventory_item_merges_the_same_concrete_instance():
    actor = _actor_with_inventory(InventoryItem("scene:plank", "Deska", "material", quantity=1))

    updated = add_inventory_item(actor, InventoryItem("scene:plank", "Deska", "material", quantity=2))

    assert updated.inventory[0].quantity == 3
