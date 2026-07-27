import pytest

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.inventory import (
    InventoryItem,
    ItemChargeRecovery,
    consume_item_use,
    has_item_use,
    recover_item_charges,
)
from dnd_board_game.world import Coordinate


def _actor(*items: InventoryItem) -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=12,
        hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        inventory=items,
    )


def _wand(
    *,
    current: int = 3,
    recovery: ItemChargeRecovery = ItemChargeRecovery.LONG_REST,
    recovery_dice: str | None = None,
    recovery_modifier: int = 0,
) -> InventoryItem:
    return InventoryItem(
        "binding_wand",
        "Różdżka oplątania",
        "magic_item",
        equipped=False,
        charges_maximum=7,
        charges_current=current,
        charges_recovery=recovery,
        charges_recovery_dice=recovery_dice,
        charges_recovery_modifier=recovery_modifier,
    )


def test_charge_use_spends_requested_amount_without_consuming_item() -> None:
    actor = _actor(_wand(current=3))

    result = consume_item_use(actor, "binding_wand", charge_cost=2)

    assert result.spent == 2
    assert result.item.charges_current == 1
    assert result.item.quantity == 1
    assert has_item_use(result.actor, "binding_wand", charge_cost=1)
    assert not has_item_use(result.actor, "binding_wand", charge_cost=2)


def test_charge_use_rejects_depleted_or_non_charge_item() -> None:
    actor = _actor(
        _wand(current=0),
        InventoryItem("flask", "Fiolka", "consumable", equipped=False),
    )

    assert not has_item_use(actor, "binding_wand", charge_cost=1)
    assert not has_item_use(actor, "flask", charge_cost=1)


def test_charge_configuration_rejects_stacks_and_incomplete_recovery() -> None:
    with pytest.raises(ValueError, match="cannot be stacked"):
        InventoryItem(
            "stacked_wand",
            "Stos różdżek",
            "magic_item",
            quantity=2,
            charges_maximum=3,
        )
    with pytest.raises(ValueError, match="requires charges_recovery_dice"):
        InventoryItem(
            "invalid_wand",
            "Błędna różdżka",
            "magic_item",
            charges_maximum=3,
            charges_recovery=ItemChargeRecovery.LONG_REST,
            charges_recovery_modifier=1,
        )


def test_fixed_recovery_restores_to_maximum_and_long_rest_includes_short_rest_items() -> None:
    actor = _actor(
        _wand(current=1),
        InventoryItem(
            "amulet",
            "Amulet",
            "magic_item",
            equipped=False,
            charges_maximum=2,
            charges_current=0,
            charges_recovery=ItemChargeRecovery.SHORT_REST,
        ),
    )

    result = recover_item_charges(actor, ItemChargeRecovery.LONG_REST)

    assert [item.charges_current for item in result.actor.inventory] == [7, 2]
    assert {entry.item_id for entry in result.recoveries} == {
        "binding_wand",
        "amulet",
    }


def test_random_recovery_uses_injected_dice_and_caps_at_maximum() -> None:
    actor = _actor(
        _wand(
            current=2,
            recovery_dice="1d6",
            recovery_modifier=1,
        )
    )

    result = recover_item_charges(
        actor,
        ItemChargeRecovery.LONG_REST,
        roll_die=lambda sides: 4 if sides == 6 else 1,
    )

    assert result.actor.inventory[0].charges_current == 7
    assert result.recoveries[0].rolls == (4,)
    assert result.recoveries[0].recovered == 5
