from dnd_board_game.inventory import (
    HandSlot,
    InventoryItem,
    free_hand_count,
    hand_loadout,
    normalize_hand_equipment,
    plan_hand_equip,
)


def test_legacy_equipped_one_handed_weapons_fill_both_explicit_slots() -> None:
    items = (
        InventoryItem("sword", "Miecz", "weapon"),
        InventoryItem("dagger", "Sztylet", "weapon", light_weapon=True),
    )

    normalized = normalize_hand_equipment(items)
    loadout = hand_loadout(normalized)

    assert loadout.main_hand_item_id == "sword"
    assert loadout.off_hand_item_id == "dagger"
    assert normalized[0].held_in == (HandSlot.MAIN_HAND,)
    assert normalized[1].held_in == (HandSlot.OFF_HAND,)
    assert free_hand_count(normalized) == 0


def test_two_handed_weapon_occupies_both_slots_and_unequips_later_weapon() -> None:
    items = (
        InventoryItem("crossbow", "Kusza", "weapon", hands_required=2),
        InventoryItem("dagger", "Sztylet", "weapon"),
    )

    normalized = normalize_hand_equipment(items)

    assert normalized[0].held_in == (HandSlot.MAIN_HAND, HandSlot.OFF_HAND)
    assert normalized[1].equipped is False
    assert normalized[1].held_in == ()
    assert free_hand_count(normalized) == 0


def test_equipping_second_one_handed_weapon_preserves_main_hand() -> None:
    items = (
        InventoryItem("sword", "Miecz", "weapon"),
        InventoryItem("dagger", "Sztylet", "weapon", equipped=False),
    )

    plan = plan_hand_equip(items, "dagger")

    assert plan.replaced_item_ids == ()
    assert plan.occupied_slots == (HandSlot.OFF_HAND,)
    assert {item.id for item in plan.inventory if item.equipped} == {"sword", "dagger"}


def test_equipping_two_handed_weapon_replaces_items_in_both_hands() -> None:
    items = (
        InventoryItem("sword", "Miecz", "weapon"),
        InventoryItem("dagger", "Sztylet", "weapon"),
        InventoryItem("crossbow", "Kusza", "weapon", equipped=False, hands_required=2),
    )

    plan = plan_hand_equip(items, "crossbow")

    assert plan.replaced_item_ids == ("sword", "dagger")
    assert plan.occupied_slots == (HandSlot.MAIN_HAND, HandSlot.OFF_HAND)
    assert [item.id for item in plan.inventory if item.equipped] == ["crossbow"]


def test_reserved_grapple_hand_reduces_available_free_hand_count() -> None:
    items = (InventoryItem("sword", "Miecz", "weapon"),)

    assert free_hand_count(items) == 1
    assert free_hand_count(items, reserved_hands=1) == 0
