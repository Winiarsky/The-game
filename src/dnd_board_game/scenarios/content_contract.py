from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dnd_board_game.core import MigrationError, MigrationRegistry


SCENARIO_SCHEMA = "dnd_board_game.scenario"
SCENARIO_SCHEMA_VERSION = 1
RULESET_DND_5E_2014 = "dnd_5e_2014"
SOURCE_PACK_REGISTRY_SCHEMA = "dnd_board_game.source_packs"
SOURCE_PACK_REGISTRY_VERSION = 1

_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")

_SCENARIO_MIGRATIONS = MigrationRegistry(
    schema=SCENARIO_SCHEMA,
    current_version=SCENARIO_SCHEMA_VERSION,
)


@dataclass(frozen=True, slots=True)
class ContentHeader:
    schema: str
    schema_version: int
    ruleset_id: str
    source_pack_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SourcePack:
    id: str
    name: str
    license_id: str
    source_url: str
    attribution: str
    redistributable: bool


def validate_stable_id(value: str, field: str) -> str:
    if not _STABLE_ID.fullmatch(value):
        raise ValueError(
            f"{field} must be a stable snake_case id containing lowercase letters, "
            "digits and underscores."
        )
    return value


def parse_content_header(
    data: dict[str, Any],
    *,
    expected_schema: str,
    context: str,
    legacy_defaults: bool = False,
) -> ContentHeader:
    schema = data.get("schema")
    schema_version = data.get("schema_version")
    ruleset_id = data.get("ruleset_id")
    source_pack_ids = data.get("source_pack_ids")
    if legacy_defaults:
        schema = schema or expected_schema
        schema_version = 1 if schema_version is None else schema_version
        ruleset_id = ruleset_id or RULESET_DND_5E_2014
        source_pack_ids = source_pack_ids or ["project_original"]
    if schema != expected_schema:
        raise ValueError(f"{context}.schema must be {expected_schema!r}.")
    if (
        not isinstance(schema_version, int)
        or isinstance(schema_version, bool)
        or schema_version != SCENARIO_SCHEMA_VERSION
    ):
        raise ValueError(
            f"{context}.schema_version must be {SCENARIO_SCHEMA_VERSION}."
        )
    if not isinstance(ruleset_id, str) or not ruleset_id:
        raise ValueError(f"{context}.ruleset_id must be a non-empty string.")
    if (
        not isinstance(source_pack_ids, list)
        or not source_pack_ids
        or not all(isinstance(value, str) and value for value in source_pack_ids)
    ):
        raise ValueError(
            f"{context}.source_pack_ids must be a non-empty list of ids."
        )
    if len(set(source_pack_ids)) != len(source_pack_ids):
        raise ValueError(f"{context}.source_pack_ids cannot contain duplicates.")
    return ContentHeader(
        schema=expected_schema,
        schema_version=schema_version,
        ruleset_id=ruleset_id,
        source_pack_ids=tuple(source_pack_ids),
    )


def migrate_scenario_payload(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MigrationError("Scenario payload must be an object.")
    normalized = dict(raw)
    normalized.setdefault("schema", SCENARIO_SCHEMA)
    normalized.setdefault("schema_version", 1)
    normalized.setdefault("ruleset_id", RULESET_DND_5E_2014)
    normalized.setdefault("source_pack_ids", ["project_original"])
    return _SCENARIO_MIGRATIONS.migrate(normalized)


def load_source_pack_registry(path: str | Path) -> dict[str, SourcePack]:
    registry_path = Path(path)
    try:
        raw = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load source-pack registry {registry_path}: {exc}.") from exc
    if not isinstance(raw, dict):
        raise ValueError("Source-pack registry must be an object.")
    if raw.get("schema") != SOURCE_PACK_REGISTRY_SCHEMA:
        raise ValueError("Unknown source-pack registry schema.")
    if raw.get("schema_version") != SOURCE_PACK_REGISTRY_VERSION:
        raise ValueError("Unsupported source-pack registry version.")
    entries = raw.get("source_packs")
    if not isinstance(entries, list):
        raise ValueError("source_packs must be a list.")
    result: dict[str, SourcePack] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"source_packs[{index}] must be an object.")
        pack_id = validate_stable_id(
            str(entry.get("id", "")),
            f"source_packs[{index}].id",
        )
        if pack_id in result:
            raise ValueError(f"Duplicate source pack id: {pack_id}.")
        result[pack_id] = SourcePack(
            id=pack_id,
            name=str(entry.get("name", "")),
            license_id=str(entry.get("license_id", "")),
            source_url=str(entry.get("source_url", "")),
            attribution=str(entry.get("attribution", "")),
            redistributable=bool(entry.get("redistributable", False)),
        )
    return result
