from dataclasses import replace
import json

import pytest

from dnd_board_game.actors import AbilityScores
from dnd_board_game.character_creation import (
    CharacterDraft,
    CharacterRoster,
    build_character,
    load_character_catalog,
    load_character_resources,
)


def fighter_draft() -> CharacterDraft:
    return CharacterDraft(
        id="aldren",
        name="Aldren",
        species_id="human",
        class_id="fighter",
        background_id="soldier",
        base_ability_scores=AbilityScores(15, 14, 13, 12, 10, 8),
        selected_skill_ids=("perception", "survival"),
        selected_fighting_style_id="defense",
        equipment_package_id="fighter_sword_and_board",
        selected_species_language_ids=("elvish",),
        selected_background_tool_ids=("dice_set",),
    )


@pytest.fixture
def roster(tmp_path):
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    return (
        CharacterRoster(tmp_path / "characters", catalog, resources),
        catalog,
        resources,
    )


def test_roster_round_trip_rebuilds_and_sorts_characters(roster) -> None:
    storage, catalog, resources = roster
    aldren = build_character(fighter_draft(), catalog, resources)
    brenna = build_character(
        replace(fighter_draft(), id="brenna", name="Brenna"),
        catalog,
        resources,
    )

    storage.save(brenna)
    storage.save(aldren)
    scan = storage.scan()

    assert [item.actor.name for item in scan.characters] == ["Aldren", "Brenna"]
    assert scan.errors == ()
    assert storage.load("aldren") == aldren


def test_roster_refuses_overwrite_and_path_traversal(roster) -> None:
    storage, catalog, resources = roster
    character = build_character(fighter_draft(), catalog, resources)
    storage.save(character)

    with pytest.raises(ValueError, match="już istnieje"):
        storage.save(character)
    with pytest.raises(ValueError, match="Nieprawidłowe id"):
        storage.load("../aldren")


def test_roster_scan_isolates_invalid_record_and_delete_is_recoverable(roster) -> None:
    storage, catalog, resources = roster
    character = build_character(fighter_draft(), catalog, resources)
    path = storage.save(character)
    broken = storage.root / "broken.character.json"
    broken.write_text(json.dumps({"schema": "wrong"}), encoding="utf-8")

    scan = storage.scan()
    deleted_path = storage.delete("aldren")

    assert [item.actor.name for item in scan.characters] == ["Aldren"]
    assert len(scan.errors) == 1
    assert scan.errors[0].path == broken
    assert not path.exists()
    assert deleted_path.is_file()


def test_roster_updates_runtime_experience_without_persisting_encounter_hp(
    roster,
) -> None:
    storage, catalog, resources = roster
    character = build_character(fighter_draft(), catalog, resources)
    storage.save(character)

    updated = storage.update_experience("aldren", 300)
    restored = storage.load("aldren")

    assert updated.actor.experience_points == 300
    assert restored.actor.experience_points == 300
    assert restored.actor.hp == restored.actor.max_hp
    assert restored.actor.level == 1
