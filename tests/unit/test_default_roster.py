from pathlib import Path

from dnd_board_game.character_creation import (
    build_character,
    default_character_drafts,
    load_character_catalog,
    load_character_resources,
    validate_character_draft,
)
from dnd_board_game.inventory import effective_armor_class
from dnd_board_game.scenarios.loader import compile_actor_combat_content


def test_default_roster_has_one_valid_playable_character_per_class():
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    drafts = default_character_drafts()

    assert len(drafts) == len(catalog.classes) == 12
    assert {draft.class_id for draft in drafts} == {
        character_class.id for character_class in catalog.classes
    }
    assert len({draft.id for draft in drafts}) == len(drafts)

    for draft in drafts:
        validation = validate_character_draft(draft, catalog)
        assert validation.valid, (draft.id, validation.issues)
        character = build_character(draft, catalog, resources)
        actor = character.actor
        assert actor.level == 1
        assert actor.hp == actor.max_hp > 0
        assert effective_armor_class(actor) >= 10
        assert actor.proficiencies.skills
        assert actor.inventory
        assert actor.features
        assert actor.portrait.startswith("character_uploads/default_roster/")
        assert (
            Path("assets/character_portraits/default_roster")
            / Path(actor.portrait).name
        ).is_file()
        assert compile_actor_combat_content(actor).attack_sources


def test_default_roster_spellcasters_have_legal_actions_and_resources():
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    spellcasters = {"bard", "cleric", "druid", "sorcerer", "warlock", "wizard"}

    for draft in default_character_drafts():
        if draft.class_id not in spellcasters:
            continue
        actor = build_character(draft, catalog, resources).actor
        assert actor.spells
        assert actor.spell_access is not None
        assert actor.spell_slots is not None


def test_default_roster_core_class_mechanics_are_attached():
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    actors = {
        draft.class_id: build_character(draft, catalog, resources).actor
        for draft in default_character_drafts()
    }

    expected_features = {
        "barbarian": "rage",
        "bard": "bardic_inspiration",
        "cleric": "disciple_of_life",
        "druid": "spellcasting",
        "fighter": "second_wind",
        "monk": "martial_arts",
        "paladin": "lay_on_hands",
        "ranger": "favored_enemy",
        "rogue": "sneak_attack",
        "sorcerer": "draconic_resilience",
        "warlock": "dark_ones_blessing",
        "wizard": "arcane_recovery",
    }
    for class_id, feature_id in expected_features.items():
        assert feature_id in {
            feature.feature_id for feature in actors[class_id].features
        }

    assert any(
        pool.id == "rage_uses" and pool.maximum == 2
        for pool in actors["barbarian"].resource_pools
    )
    assert any(
        pool.id == "lay_on_hands_points" and pool.maximum == 5
        for pool in actors["paladin"].resource_pools
    )
