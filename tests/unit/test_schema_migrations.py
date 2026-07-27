import pytest

from dnd_board_game.core import MigrationError, MigrationRegistry
from dnd_board_game.scenarios import migrate_scenario_payload


def test_migration_registry_applies_every_version_in_order() -> None:
    registry = MigrationRegistry("test.schema", current_version=3)
    registry.register(
        1,
        lambda data: {
            **data,
            "schema_version": 2,
            "steps": [*data.get("steps", []), "v1_to_v2"],
        },
    )
    registry.register(
        2,
        lambda data: {
            **data,
            "schema_version": 3,
            "steps": [*data.get("steps", []), "v2_to_v3"],
        },
    )

    migrated = registry.migrate(
        {"schema": "test.schema", "schema_version": 1}
    )

    assert migrated["schema_version"] == 3
    assert migrated["steps"] == ["v1_to_v2", "v2_to_v3"]


def test_migration_registry_rejects_a_missing_step() -> None:
    registry = MigrationRegistry("test.schema", current_version=3)
    registry.register(
        2,
        lambda data: {**data, "schema_version": 3},
    )

    with pytest.raises(MigrationError, match="Missing migration"):
        registry.migrate({"schema": "test.schema", "schema_version": 1})


def test_migration_registry_rejects_future_versions() -> None:
    registry = MigrationRegistry("test.schema", current_version=2)

    with pytest.raises(MigrationError, match="supported range"):
        registry.migrate({"schema": "test.schema", "schema_version": 3})


def test_legacy_scenario_header_is_normalized_to_v1() -> None:
    migrated = migrate_scenario_payload({"id": "test_scenario"})

    assert migrated["schema"] == "dnd_board_game.scenario"
    assert migrated["schema_version"] == 1
    assert migrated["ruleset_id"] == "dnd_5e_2014"
    assert migrated["source_pack_ids"] == ["project_original"]


def test_scenario_migration_rejects_future_content_version() -> None:
    with pytest.raises(MigrationError, match="supported range"):
        migrate_scenario_payload(
            {
                "schema": "dnd_board_game.scenario",
                "schema_version": 2,
            }
        )
