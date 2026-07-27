import json
from pathlib import Path

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    ProficiencyProfile,
    ability_check_roll_modifiers,
)
from dnd_board_game.inventory import (
    CheckModifierMode,
    GearCategory,
    SpellcastingFocusKind,
    advance_active_light,
    can_store_in_container,
    expand_equipment_pack,
    gear_check_modifier,
    ignite_light_source,
    set_light_hood,
    unpack_equipment_pack,
)
from dnd_board_game.scenarios.loader import (
    _inventory_item_from_item_data,
    _load_item_property_catalog,
    _parse_item_definition,
    _read_item_definition,
)
from dnd_board_game.world import Coordinate


CONTENT_SCENARIO = Path("content/scenarios/village_square_mvp.json")
CATALOG_PATH = Path("content/items/adventuring_gear.json")


def _item(item_id: str):
    properties = _load_item_property_catalog(CONTENT_SCENARIO)
    data = _read_item_definition(CONTENT_SCENARIO, item_id)
    return _inventory_item_from_item_data(
        data,
        quantity=1,
        equipped=False,
        source_ref=item_id,
        property_catalog=properties,
    )


def _actor(*item_ids: str) -> Actor:
    return Actor(
        ActorId("hero"),
        "Bohater",
        10,
        10,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        inventory=tuple(_item(item_id) for item_id in item_ids),
    )


def test_complete_srd_adventuring_gear_catalog_uses_one_schema() -> None:
    data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    items = data["items"]
    ids = [item["id"] for item in items]
    properties = _load_item_property_catalog(CONTENT_SCENARIO)

    assert data["source_pack_ids"] == ["srd_5_1_cc_by_4_0"]
    assert len(items) == 144
    assert len(ids) == len(set(ids))
    assert sum(item["gear"]["category"] == "equipment_pack" for item in items) == 7
    assert sum(item["gear"]["category"] == "artisans_tool" for item in items) == 17
    assert sum(item["gear"]["category"] == "musical_instrument" for item in items) == 10
    assert all(
        _parse_item_definition(item, properties, f"item {item['id']}")
        for item in items
    )


def test_spellcasting_gear_is_typed_for_m7() -> None:
    crystal = _item("arcane_focus_crystal")
    mistletoe = _item("druidic_focus_mistletoe")
    symbol = _item("holy_symbol_amulet")
    pouch = _item("component_pouch")
    spellbook = _item("spellbook")

    assert crystal.spellcasting_focus_kind == SpellcastingFocusKind.ARCANE
    assert mistletoe.spellcasting_focus_kind == SpellcastingFocusKind.DRUIDIC
    assert symbol.spellcasting_focus_kind == SpellcastingFocusKind.HOLY_SYMBOL
    assert pouch.spellcasting_focus_kind == SpellcastingFocusKind.COMPONENT_POUCH
    assert spellbook.gear_category == GearCategory.SPELLCASTING_GEAR
    assert spellbook.stackable is False


def test_container_capacity_validates_weight_liquid_ammunition_and_sheets() -> None:
    backpack = _item("backpack").container_capacity
    waterskin = _item("waterskin").container_capacity
    quiver = _item("quiver").container_capacity
    scroll_case = _item("map_scroll_case").container_capacity

    assert backpack is not None and can_store_in_container(backpack, weight_lb=30)
    assert not can_store_in_container(backpack, weight_lb=30.1)
    assert waterskin is not None and can_store_in_container(waterskin, liquid_pints=4)
    assert not can_store_in_container(waterskin, liquid_pints=5)
    assert quiver is not None and can_store_in_container(
        quiver,
        ammunition_type="arrow",
        ammunition_count=20,
    )
    assert not can_store_in_container(
        quiver,
        ammunition_type="crossbow_bolt",
        ammunition_count=1,
    )
    assert scroll_case is not None and not can_store_in_container(
        scroll_case,
        sheet_count=11,
    )


def test_light_sources_consume_the_source_or_fuel_and_expire() -> None:
    candle_result = ignite_light_source(_actor("candle"), "candle")
    assert candle_result.actor.inventory[0].quantity == 0
    assert candle_result.actor.active_light == candle_result.active_light
    assert candle_result.active_light.bright_distance_feet == 5
    assert advance_active_light(candle_result.active_light, 59).remaining_minutes == 1
    assert advance_active_light(candle_result.active_light, 60) is None

    lamp_result = ignite_light_source(_actor("hooded_lantern", "oil_flask"), "hooded_lantern")
    assert next(
        item for item in lamp_result.actor.inventory if item.id == "hooded_lantern"
    ).quantity == 1
    assert next(
        item for item in lamp_result.actor.inventory if item.id == "oil_flask"
    ).quantity == 0
    hooded = set_light_hood(lamp_result.active_light, True)
    assert hooded.current_bright_distance_feet == 0
    assert hooded.current_dim_additional_feet == 5


def test_utility_modifiers_and_durability_are_data_driven() -> None:
    crowbar = _item("crowbar")
    tackle = _item("block_and_tackle")
    ram = _item("portable_ram")
    manacles = _item("manacles")

    crowbar_rule = gear_check_modifier(
        crowbar,
        context="leverage",
        ability="strength",
    )
    ram_rule = gear_check_modifier(
        ram,
        context="break_door",
        ability="strength",
    )
    tackle_rule = gear_check_modifier(tackle, context="hoist_weight")
    assert crowbar_rule is not None and crowbar_rule.mode == CheckModifierMode.ADVANTAGE
    assert ram_rule is not None and ram_rule.value == 4
    assert tackle_rule is not None
    assert tackle_rule.mode == CheckModifierMode.MULTIPLIER
    assert tackle_rule.value == 4
    assert manacles.durability is not None
    assert manacles.durability.hit_points == 15
    assert manacles.durability.escape_dexterity_dc == 20
    assert manacles.durability.pick_lock_dc == 15


def test_catalog_tool_proficiency_id_uses_the_real_item_label() -> None:
    supplies = _item("calligraphers_supplies")
    actor = Actor(
        ActorId("scribe"),
        "Skryba",
        10,
        10,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        ability_scores=AbilityScores(dexterity=14),
        proficiency_bonus=2,
        proficiencies=ProficiencyProfile(tools=("calligraphers_supplies",)),
        inventory=(supplies,),
    )

    modifiers = ability_check_roll_modifiers(
        actor,
        "dexterity",
        tool="calligraphers_supplies",
    )

    assert [(modifier.value, modifier.label) for modifier in modifiers] == [
        (2, "Zręczność"),
        (2, "Biegłość: Przybory kaligrafa"),
    ]


def test_equipment_pack_expands_to_real_catalog_items_and_quantities() -> None:
    pack = _item("explorers_pack")
    catalog = {
        entry.item_id: _item(entry.item_id)
        for entry in pack.bundle_contents
    }

    expanded = expand_equipment_pack(pack, catalog)
    quantities = {item.id: item.quantity for item in expanded}

    assert quantities["torch"] == 10
    assert quantities["rations"] == 10
    assert quantities["hempen_rope"] == 1
    assert all(item.equipped is False for item in expanded)

    actor = Actor(
        ActorId("packer"),
        "Pakowacz",
        10,
        10,
        0,
        30,
        Coordinate(0, 0),
        Faction.ALLY,
        inventory=(pack,),
    )
    unpacked = unpack_equipment_pack(actor, pack.id, catalog)
    assert next(item for item in unpacked.inventory if item.id == pack.id).quantity == 0
    assert next(item for item in unpacked.inventory if item.id == "torch").quantity == 10
