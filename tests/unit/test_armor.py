from dataclasses import replace
import json
from pathlib import Path

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    Faction,
    ProficiencyProfile,
)
from dnd_board_game.inventory import (
    ArmorCategory,
    HandSlot,
    InventoryItem,
    doff_armor,
    don_armor,
    effective_armor_class,
    effective_speed_feet,
    has_stealth_disadvantage,
)
from dnd_board_game.world import Coordinate


def _armor(
    item_id: str,
    category: ArmorCategory,
    base_ac: int,
    *,
    equipped: bool = False,
    dexterity_cap: int | None = None,
    strength_requirement: int | None = None,
    stealth_disadvantage: bool = False,
) -> InventoryItem:
    return InventoryItem(
        item_id,
        item_id.replace("_", " ").title(),
        "armor",
        equipped=equipped,
        armor_category=category,
        armor_base_ac=base_ac,
        armor_dexterity_cap=dexterity_cap,
        armor_strength_requirement=strength_requirement,
        stealth_disadvantage=stealth_disadvantage,
        armor_proficiency=category.value,
    )


def _actor(*items: InventoryItem, strength: int = 12, dexterity: int = 16) -> Actor:
    return Actor(
        id=ActorId("hero"),
        name="Bohater",
        ac=13,
        hp=20,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        ability_scores=AbilityScores(strength=strength, dexterity=dexterity),
        inventory=items,
        proficiencies=ProficiencyProfile(armor=("light", "medium", "heavy", "shield")),
    )


def test_body_armor_uses_category_dexterity_formula_and_shield_bonus() -> None:
    shield = InventoryItem(
        "shield",
        "Tarcza",
        "shield",
        equipped=True,
        hands_required=1,
        held_in=(HandSlot.OFF_HAND,),
        armor_class_bonus=2,
        armor_proficiency="shield",
    )

    assert effective_armor_class(_actor(_armor("leather", ArmorCategory.LIGHT, 11, equipped=True))) == 14
    assert effective_armor_class(
        _actor(
            _armor(
                "chain_shirt",
                ArmorCategory.MEDIUM,
                13,
                equipped=True,
                dexterity_cap=2,
            ),
            shield,
        )
    ) == 17
    assert effective_armor_class(
        _actor(
            _armor(
                "chain_mail",
                ArmorCategory.HEAVY,
                16,
                equipped=True,
                dexterity_cap=0,
            )
        )
    ) == 16


def test_don_and_doff_armor_validate_proficiency_conflicts_and_time() -> None:
    leather = _armor("leather", ArmorCategory.LIGHT, 11)
    chain_mail = _armor(
        "chain_mail",
        ArmorCategory.HEAVY,
        16,
        dexterity_cap=0,
    )
    actor = _actor(leather, chain_mail)

    donned = don_armor(actor, "leather")
    conflict = don_armor(donned.actor, "chain_mail")
    doffed = doff_armor(donned.actor, "leather")

    assert donned.accepted and donned.elapsed_minutes == 1
    assert effective_armor_class(donned.actor) == 14
    assert not conflict.accepted
    assert "Najpierw trzeba zdjąć" in conflict.message
    assert doffed.accepted and doffed.elapsed_minutes == 1
    assert effective_armor_class(doffed.actor) == actor.ac

    untrained = replace(actor, proficiencies=ProficiencyProfile())
    rejected = don_armor(untrained, "leather")
    assert not rejected.accepted
    assert "biegłości" in rejected.message


def test_heavy_armor_strength_requirement_reduces_speed_and_stealth() -> None:
    chain_mail = _armor(
        "chain_mail",
        ArmorCategory.HEAVY,
        16,
        equipped=True,
        dexterity_cap=0,
        strength_requirement=13,
        stealth_disadvantage=True,
    )

    weak = _actor(chain_mail, strength=12)
    strong = _actor(chain_mail, strength=13)

    assert effective_speed_feet(weak) == 20
    assert effective_speed_feet(strong) == 30
    assert has_stealth_disadvantage(weak)


def test_broken_or_unequipped_body_armor_falls_back_to_actor_ac() -> None:
    leather = _armor("leather", ArmorCategory.LIGHT, 11, equipped=True)
    actor = _actor(leather)

    assert effective_armor_class(replace(actor, inventory=(replace(leather, broken=True),))) == 13
    assert effective_armor_class(replace(actor, inventory=(replace(leather, equipped=False),))) == 13


def test_multiple_equipped_body_armors_are_rejected() -> None:
    actor = _actor(
        _armor("leather", ArmorCategory.LIGHT, 11, equipped=True),
        _armor(
            "chain_shirt",
            ArmorCategory.MEDIUM,
            13,
            equipped=True,
            dexterity_cap=2,
        ),
    )

    try:
        effective_armor_class(actor)
    except ValueError as exc:
        assert "tylko jeden pancerz" in str(exc)
    else:
        raise AssertionError("Multiple equipped body armors should be rejected.")


def test_srd_armor_catalog_contains_all_twelve_body_armors() -> None:
    armors = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in Path("content/items").glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("kind") == "armor"
    ]

    assert len(armors) == 12
    assert sum(item["armor_category"] == "light" for item in armors) == 3
    assert sum(item["armor_category"] == "medium" for item in armors) == 5
    assert sum(item["armor_category"] == "heavy" for item in armors) == 4
    assert all(item["source_pack_ids"] == ["srd_5_1_cc_by_4_0"] for item in armors)
