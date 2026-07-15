import pytest

from dnd_board_game.exploration import SceneFixture
from dnd_board_game.inventory import (
    ItemDefinition,
    ItemInstance,
    ItemPropertyCatalog,
    ItemPropertyDefinition,
)


def _catalog() -> ItemPropertyCatalog:
    return ItemPropertyCatalog(
        schema_version=1,
        properties=(
            ItemPropertyDefinition("long", "długie"),
            ItemPropertyDefinition("rigid", "sztywne"),
            ItemPropertyDefinition("fragile", "kruche"),
        ),
    )


def test_item_instance_combines_definition_and_local_property_overrides() -> None:
    definition = ItemDefinition(
        id="wooden_plank",
        name="Drewniana deska",
        kind="material",
        properties=("long", "rigid"),
    )

    item = ItemInstance(
        id="rotten_plank",
        definition=definition,
        quantity=4,
        condition="rotten",
        added_properties=("fragile",),
        removed_properties=("rigid",),
    )

    assert item.definition_id == "wooden_plank"
    assert item.properties == frozenset({"long", "fragile"})
    assert item.usable is True


def test_item_property_catalog_rejects_unknown_properties() -> None:
    with pytest.raises(ValueError, match="unknown item properties: magical"):
        _catalog().validate(("long", "magical"), "test.properties")


def test_item_instance_rejects_conflicting_local_property_overrides() -> None:
    definition = ItemDefinition("wooden_plank", "Deska", "material", properties=("rigid",))

    with pytest.raises(ValueError, match="cannot add and remove the same properties: rigid"):
        ItemInstance(
            id="conflicting_plank",
            definition=definition,
            added_properties=("rigid",),
            removed_properties=("rigid",),
        )


def test_scene_fixture_keeps_possible_material_yields_separate_from_current_items() -> None:
    scrap_definition = ItemDefinition(
        id="scrap_metal",
        name="Metalowy element",
        kind="material",
        properties=("rigid",),
    )
    yielded_scrap = ItemInstance(
        id="detached_metal",
        definition=scrap_definition,
        quantity=2,
        available=False,
    )

    fixture = SceneFixture(
        id="gate_hinges",
        name="Zawiasy",
        properties=("rigid",),
        detachable=True,
        yield_items=(yielded_scrap,),
    )

    assert fixture.detachable is True
    assert fixture.portable is False
    assert fixture.yield_items == (yielded_scrap,)
