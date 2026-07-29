from dnd_board_game.scenarios import (
    RULESET_DND_5E_2014,
    SCENARIO_SCHEMA,
    audit_content,
    load_source_pack_registry,
)


def test_repository_content_audit_has_no_errors() -> None:
    report = audit_content("content")

    assert report.ok is True
    assert report.scenario_ids == (
        "abandoned_watchtower",
        "first_playable_scene",
        "gate_skirmish",
        "goblin_ambush",
        "mechanics_playground",
        "mechanics_playground_arena",
        "movement_skirmish",
        "multi_actor_skirmish",
        "village_square_mvp",
    )
    assert {entry.stable_id for entry in report.entries} >= {
        "scenario:abandoned_watchtower",
        "monster:goblin",
        "item:longsword",
        "feature:heroic_strike",
        "species:human",
        "class:fighter",
        "subclass:life_domain",
        "background:soldier",
    }
    assert all(entry.schema_version == 1 for entry in report.entries)
    assert all(entry.ruleset_id == RULESET_DND_5E_2014 for entry in report.entries)
    assert next(
        entry
        for entry in report.entries
        if entry.stable_id == "scenario:abandoned_watchtower"
    ).schema == SCENARIO_SCHEMA


def test_source_pack_registry_contains_official_srd_attribution() -> None:
    registry = load_source_pack_registry("content/source_packs.json")

    srd = registry["srd_5_1_cc_by_4_0"]
    assert srd.license_id == "CC-BY-4.0"
    assert srd.redistributable is True
    assert "System Reference Document 5.1" in srd.attribution
