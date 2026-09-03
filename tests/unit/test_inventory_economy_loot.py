import pytest

from dnd_board_game.actors import AbilityScores, Actor, ActorId, Faction
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.inventory.economy import (
    CurrencyWallet,
    carried_weight_lb,
    carrying_capacity_lb,
)
from dnd_board_game.inventory.loot import (
    LootBundle,
    loot_bundle_from_actor,
    merge_loot_bundles,
    transfer_actor_loot,
    transfer_all_actor_loot,
    transfer_all_loot,
    transfer_loot,
)
from dnd_board_game.scenarios import build_encounter_from_scenario, load_scenario
from dnd_board_game.world import Coordinate


def _actor(
    actor_id: str,
    *,
    faction: Faction,
    strength: int = 10,
    inventory: tuple[InventoryItem, ...] = (),
    currency: CurrencyWallet = CurrencyWallet(),
) -> Actor:
    return Actor(
        id=ActorId(actor_id),
        name=actor_id,
        ac=10,
        hp=0 if faction == Faction.ENEMY else 10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=faction,
        ability_scores=AbilityScores(strength=strength),
        inventory=inventory,
        currency=currency,
    )


def test_wallet_value_coin_weight_and_standard_carrying_capacity():
    actor = _actor(
        "hero",
        faction=Faction.ALLY,
        strength=8,
        inventory=(InventoryItem("rope", "Lina", "gear", quantity=2, weight_lb=10),),
        currency=CurrencyWallet(cp=25, gp=1),
    )

    assert actor.currency.total_cp == 125
    assert carried_weight_lb(actor) == pytest.approx(20.52)
    assert carrying_capacity_lb(actor) == 120


def test_actor_loot_excludes_equipped_dropped_and_nonportable_items():
    source = _actor(
        "goblin",
        faction=Faction.ENEMY,
        inventory=(
            InventoryItem("scimitar", "Szabla", "weapon", equipped=False, weight_lb=3),
            InventoryItem("poison", "Trucizna", "consumable", equipped=False, weight_lb=0.5),
            InventoryItem("armor", "Pancerz", "armor", equipped=True, weight_lb=10),
            InventoryItem("altar", "Ołtarz", "fixture", equipped=False, portable=False),
        ),
        currency=CurrencyWallet(sp=5),
    )

    bundle = loot_bundle_from_actor(source, excluded_item_ids=frozenset({"scimitar"}))

    assert [item.id for item in bundle.items] == ["poison"]
    assert bundle.currency == CurrencyWallet(sp=5)


def test_transfer_all_loot_is_atomic_and_moves_items_and_currency():
    source = _actor(
        "goblin",
        faction=Faction.ENEMY,
        inventory=(InventoryItem("poison", "Trucizna", "consumable", equipped=False, weight_lb=0.5),),
        currency=CurrencyWallet(sp=5),
    )
    recipient = _actor("hero", faction=Faction.ALLY)

    result = transfer_all_actor_loot(source, recipient)

    assert result.source.inventory == ()
    assert result.source.currency.is_empty
    assert result.recipient.inventory[0].id == "poison"
    assert result.recipient.currency == CurrencyWallet(sp=5)
    assert source.inventory[0].id == "poison"


def test_transfer_rejects_the_whole_bundle_when_it_exceeds_capacity():
    source = _actor(
        "corpse",
        faction=Faction.ENEMY,
        inventory=(InventoryItem("statue", "Posąg", "treasure", equipped=False, weight_lb=151),),
    )
    recipient = _actor("hero", faction=Faction.ALLY, strength=10)

    with pytest.raises(ValueError, match="przekracza udźwig"):
        transfer_all_actor_loot(source, recipient)

    assert source.inventory[0].id == "statue"
    assert recipient.inventory == ()


def test_generic_loot_bundle_supports_found_corpse_or_container_sources():
    bundle = LootBundle(
        id="corpse:roadside_scout",
        label="Znalezione zwłoki",
        items=(InventoryItem("letter", "List", "quest", equipped=False, weight_lb=0.1),),
        currency=CurrencyWallet(cp=7),
    )
    recipient = _actor("hero", faction=Faction.ALLY)

    result = transfer_all_loot(bundle, recipient)

    assert result.bundle.is_empty
    assert result.recipient.inventory[0].id == "letter"
    assert result.recipient.currency.cp == 7


def test_shared_loot_merge_namespaces_items_and_never_equips_them() -> None:
    stash = LootBundle("party_stash", "Łup drużyny")
    bundle = LootBundle(
        "actor:goblin",
        "Goblin",
        items=(
            InventoryItem(
                "knife",
                "Nóż",
                "weapon",
                quantity=2,
                equipped=True,
            ),
        ),
        currency=CurrencyWallet(sp=3),
    )

    merged = merge_loot_bundles(stash, (bundle,))

    assert merged.items[0].id == "actor:goblin:knife"
    assert merged.items[0].quantity == 2
    assert not merged.items[0].equipped
    assert merged.items[0].held_in == ()
    assert merged.currency == CurrencyWallet(sp=3)


def test_partial_stack_transfer_preserves_remaining_items_and_currency():
    bundle = LootBundle(
        id="corpse:goblin",
        label="Goblin",
        items=(InventoryItem("arrow", "Strzała", "ammunition", quantity=5, equipped=False, weight_lb=0.05),),
        currency=CurrencyWallet(sp=4),
    )
    recipient = _actor("hero", faction=Faction.ALLY)

    result = transfer_loot(bundle, recipient, item_id="arrow", quantity=2)

    assert result.items[0].quantity == 2
    assert result.recipient.inventory[0].quantity == 2
    assert result.bundle.items[0].quantity == 3
    assert result.bundle.currency == CurrencyWallet(sp=4)


def test_currency_only_actor_transfer_leaves_items_on_the_source():
    source = _actor(
        "goblin",
        faction=Faction.ENEMY,
        inventory=(InventoryItem("poison", "Trucizna", "consumable", equipped=False, weight_lb=0.5),),
        currency=CurrencyWallet(cp=3, sp=5),
    )
    recipient = _actor("hero", faction=Faction.ALLY)

    result = transfer_actor_loot(
        source,
        recipient,
        currency=CurrencyWallet(sp=5),
    )

    assert result.source.inventory[0].id == "poison"
    assert result.source.currency == CurrencyWallet(cp=3)
    assert result.recipient.inventory == ()
    assert result.recipient.currency == CurrencyWallet(sp=5)


def test_selective_loot_can_take_light_item_when_whole_bundle_is_too_heavy():
    source = _actor(
        "corpse",
        faction=Faction.ENEMY,
        inventory=(
            InventoryItem("statue", "Posąg", "treasure", equipped=False, weight_lb=151),
            InventoryItem("key", "Klucz", "quest", equipped=False, weight_lb=0.1),
        ),
    )
    recipient = _actor("hero", faction=Faction.ALLY, strength=10)

    with pytest.raises(ValueError, match="przekracza udźwig"):
        transfer_all_actor_loot(source, recipient)

    result = transfer_actor_loot(source, recipient, item_id="key")

    assert [item.id for item in result.source.inventory] == ["statue"]
    assert [item.id for item in result.recipient.inventory] == ["key"]


def test_goblin_content_exposes_reference_loot_fixture():
    encounter = build_encounter_from_scenario(
        load_scenario("content/scenarios/goblin_ambush.json")
    )
    goblin = next(actor for actor in encounter.actors if str(actor.id) == "goblin")

    assert goblin.currency == CurrencyWallet(sp=5)
    assert [(item.id, item.equipped, item.weight_lb, item.value_cp) for item in goblin.inventory] == [
        ("poison_vial", False, 0.5, 10000)
    ]
