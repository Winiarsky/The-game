from dataclasses import replace

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.combat import (
    AttackSource,
    AttackSourceType,
    attack_sources_with_versatile_variants,
    versatile_two_handed_source,
    versatile_two_handed_source_is_legal,
)
from dnd_board_game.inventory import HandSlot, InventoryItem
from dnd_board_game.rules import D20RollRequest
from dnd_board_game.world import Coordinate


def _actor(*items: InventoryItem) -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=14,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        inventory=items,
    )


def _longsword() -> InventoryItem:
    return InventoryItem(
        "longsword",
        "Miecz",
        "weapon",
        hands_required=1,
        held_in=(HandSlot.MAIN_HAND,),
        versatile_damage_dice="1d10",
    )


def _source() -> AttackSource:
    return AttackSource(
        "Miecz",
        AttackSourceType.WEAPON,
        5,
        D20RollRequest(),
        id="longsword_slash",
        source_item_id="longsword",
        damage_hint="1d8 + 3 slashing",
        damage_die_sides=8,
        damage_modifier=3,
        damage_type="slashing",
        ability="strength",
    )


def test_free_second_hand_adds_two_handed_versatile_attack_variant() -> None:
    actor = _actor(_longsword())

    sources = attack_sources_with_versatile_variants(actor, (_source(),))

    assert [source.id for source in sources] == [
        "longsword_slash",
        "longsword_slash:two_handed",
    ]
    assert sources[1].name == "Miecz (oburącz)"
    assert sources[1].damage_die_sides == 10
    assert sources[1].damage_hint.startswith("1d10 + 3 slashing")


def test_occupied_or_reserved_second_hand_blocks_versatile_variant() -> None:
    dagger = InventoryItem(
        "dagger",
        "Sztylet",
        "weapon",
        hands_required=1,
        held_in=(HandSlot.OFF_HAND,),
    )

    assert versatile_two_handed_source(_actor(_longsword(), dagger), _source()) is None
    assert versatile_two_handed_source(
        _actor(_longsword()),
        _source(),
        reserved_hands=1,
    ) is None


def test_selected_variant_is_revalidated_when_second_hand_becomes_occupied() -> None:
    actor = _actor(_longsword())
    variant = versatile_two_handed_source(actor, _source())
    assert variant is not None
    dagger = InventoryItem(
        "dagger",
        "Sztylet",
        "weapon",
        hands_required=1,
        held_in=(HandSlot.OFF_HAND,),
    )

    assert versatile_two_handed_source_is_legal(actor, variant)
    assert not versatile_two_handed_source_is_legal(
        replace(actor, inventory=(*actor.inventory, dagger)),
        variant,
    )
