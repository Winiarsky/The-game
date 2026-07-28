import json
from pathlib import Path

from dnd_board_game.actors import Actor, ActorId, Faction
from dnd_board_game.character_creation import (
    SRD_CLASS_SUBCLASS_IDS,
    SRD_CLASS_SPELL_IDS,
    SRD_SPECIES_IDS,
    SRD_SPELL_IDS_BY_LEVEL,
    audit_srd_character_coverage,
    audit_character_implementation,
    audit_assisted_spell_plans,
    table_assisted_feature_exceptions,
    table_assisted_feature_riders,
    load_character_catalog,
    load_character_resources,
)
from dnd_board_game.rules import SpellAccessKind, SpellAccessProfile
from dnd_board_game.scenarios import compile_actor_combat_content
from dnd_board_game.world import Coordinate


def test_manifest_describes_complete_srd_level_three_target() -> None:
    assert len(SRD_SPECIES_IDS) == 9
    assert len(SRD_CLASS_SUBCLASS_IDS) == 12
    assert set(SRD_SPELL_IDS_BY_LEVEL) == {0, 1, 2}
    assert len(SRD_SPELL_IDS_BY_LEVEL[0]) == 24
    assert len(SRD_SPELL_IDS_BY_LEVEL[1]) == 49
    assert len(SRD_SPELL_IDS_BY_LEVEL[2]) == 54
    all_spell_ids = tuple(
        spell_id
        for spell_ids in SRD_SPELL_IDS_BY_LEVEL.values()
        for spell_id in spell_ids
    )
    assert len(all_spell_ids) == len(set(all_spell_ids))
    assert set(SRD_CLASS_SPELL_IDS) == {
        "bard", "cleric", "druid", "paladin",
        "ranger", "sorcerer", "warlock", "wizard",
    }
    assert all(
        set(spell_ids) <= set(all_spell_ids)
        for spell_ids in SRD_CLASS_SPELL_IDS.values()
    )


def test_coverage_report_confirms_complete_srd_catalog_without_aliases() -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")

    report = audit_srd_character_coverage(catalog, "content/spells")

    assert report.missing_species_ids == ()
    assert report.missing_class_ids == ()
    assert report.missing_subclass_ids == ()
    assert report.missing_spell_ids == ()
    assert "bless_attack_bonus" not in report.missing_spell_ids
    assert "cleric:bless" not in report.missing_class_spell_ids
    assert "wizard:fire_bolt" not in report.missing_class_spell_ids
    assert report.missing_class_spell_ids == ()
    assert report.complete is True


def test_every_level_three_feature_and_spell_has_an_explicit_runtime_contract() -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")

    report = audit_character_implementation(catalog, "content/spells")

    assert report.missing_feature_ids == ()
    assert report.spell_count == 127
    assert report.executable_spell_count > 0
    assert report.table_assisted_spell_count == 0
    assert report.malformed_assisted_spell_ids == ()
    assert report.unsupported_spell_effect_ids == ()
    assert report.complete is True
    assert set(table_assisted_feature_exceptions()) == {
        "druidic",
        "thieves_cant",
        "pact_of_the_chain",
        "tinker",
    }
    assert set(table_assisted_feature_riders()) == {"cutting_words"}


def test_every_assisted_spell_has_a_unique_mechanical_migration_plan() -> None:
    report = audit_assisted_spell_plans("content/spells")

    assert report.assisted_spell_ids == ()
    assert report.missing_plan_ids == ()
    assert report.stale_plan_ids == ()
    assert report.duplicate_plan_ids == ()
    assert report.missing_resolver_ids == ()
    assert report.complete is True


def test_every_combat_srd_spell_compiles_into_a_runtime_source() -> None:
    catalog = load_character_catalog("content/character_creation/catalog.json")
    resources = load_character_resources(catalog, "content")
    spell_ids = {
        spell_id
        for level_spell_ids in SRD_SPELL_IDS_BY_LEVEL.values()
        for spell_id in level_spell_ids
    }
    spells = tuple(
        spell
        for spell_id, spell in resources.spells
        if spell_id in spell_ids
    )
    actor = Actor(
        id=ActorId("spell_audit"),
        name="Spell audit",
        ac=10,
        hp=10,
        max_hp=10,
        temp_hp=0,
        speed_feet=30,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        spells=spells,
        spell_access=(
            SpellAccessProfile(
                SpellAccessKind.KNOWN,
                tuple(sorted(spell_ids)),
                casting_ability="intelligence",
            ),
        ),
    )

    compiled = compile_actor_combat_content(actor)
    compiled_ids = {
        source.id
        for source in (
            *compiled.attack_sources,
            *compiled.healing_sources,
            *compiled.combat_actions,
        )
    }
    expected_ids = {
        str(raw["id"])
        for path in Path("content/spells").glob("*.json")
        if (raw := json.loads(path.read_text(encoding="utf-8"))).get("id")
        in spell_ids
        and raw.get("effect", {}).get("kind") != "exploration"
    }

    assert len(spells) == 127
    assert compiled_ids == expected_ids
