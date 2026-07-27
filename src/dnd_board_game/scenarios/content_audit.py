from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

from .content_contract import (
    ContentHeader,
    load_source_pack_registry,
    parse_content_header,
    validate_stable_id,
)
from .loader import (
    _item_attack_definitions,
    _load_item_property_catalog,
    _parse_attack,
    _parse_combat_action,
    _parse_healing_source,
    _parse_item_definition,
    _parse_spell_definition,
    _spell_effect_payload,
    load_scenario,
)


class AuditSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class ContentAuditIssue:
    severity: AuditSeverity
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity.value,
            "code": self.code,
            "path": self.path,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ContentAuditEntry:
    stable_id: str
    kind: str
    local_id: str
    path: str
    schema: str
    schema_version: int
    ruleset_id: str
    source_pack_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "stable_id": self.stable_id,
            "kind": self.kind,
            "local_id": self.local_id,
            "path": self.path,
            "schema": self.schema,
            "schema_version": self.schema_version,
            "ruleset_id": self.ruleset_id,
            "source_pack_ids": list(self.source_pack_ids),
        }


@dataclass(frozen=True, slots=True)
class ContentAuditReport:
    entries: tuple[ContentAuditEntry, ...]
    issues: tuple[ContentAuditIssue, ...]
    scenario_ids: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not any(issue.severity == AuditSeverity.ERROR for issue in self.issues)

    def as_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "summary": {
                "entries": len(self.entries),
                "scenarios": len(self.scenario_ids),
                "errors": sum(
                    issue.severity == AuditSeverity.ERROR for issue in self.issues
                ),
                "warnings": sum(
                    issue.severity == AuditSeverity.WARNING for issue in self.issues
                ),
            },
            "scenario_ids": list(self.scenario_ids),
            "entries": [entry.as_dict() for entry in self.entries],
            "issues": [issue.as_dict() for issue in self.issues],
        }


def audit_content(content_root: str | Path) -> ContentAuditReport:
    root = Path(content_root)
    issues: list[ContentAuditIssue] = []
    entries: list[ContentAuditEntry] = []
    try:
        source_packs = load_source_pack_registry(root / "source_packs.json")
    except ValueError as exc:
        source_packs = {}
        issues.append(
            _issue(
                AuditSeverity.ERROR,
                "source_pack_registry_invalid",
                root / "source_packs.json",
                str(exc),
                root,
            )
        )
    else:
        if any(pack.license_id == "NOASSERTION" for pack in source_packs.values()):
            issues.append(
                _issue(
                    AuditSeverity.WARNING,
                    "source_license_unasserted",
                    root / "source_packs.json",
                    "Co najmniej jeden source pack nie ma zadeklarowanej licencji; "
                    "nie należy publikować go jako otwartego katalogu.",
                    root,
                )
            )

    seen: dict[tuple[str, str], Path] = {}
    scenario_paths: list[Path] = []
    for path, kind, expected_schema in _definition_files(root):
        try:
            data = _read_object(path)
            header = parse_content_header(
                data,
                expected_schema=expected_schema,
                context=str(path),
            )
            local_id = _definition_id(data, path, kind)
            validate_stable_id(local_id, f"{path}.id")
            unknown_packs = set(header.source_pack_ids) - set(source_packs)
            if unknown_packs:
                raise ValueError(
                    "unknown source packs: " + ", ".join(sorted(unknown_packs))
                )
            if kind == "item_collection":
                raw_items = data.get("items")
                if not isinstance(raw_items, list):
                    raise ValueError(f"{path}.items must be a list.")
                property_catalog = _load_item_property_catalog(path)
                catalog_ids: list[str] = []
                definitions = []
                for index, raw_item in enumerate(raw_items):
                    if not isinstance(raw_item, dict):
                        raise ValueError(f"{path}.items[{index}] must be an object.")
                    item_id = _definition_id(raw_item, path, "item")
                    validate_stable_id(item_id, f"{path}.items[{index}].id")
                    definition = _parse_item_definition(
                        raw_item,
                        property_catalog,
                        f"item {item_id}",
                    )
                    for attack in _item_attack_definitions(raw_item):
                        _parse_attack(attack, f"item {item_id}")
                    catalog_ids.append(item_id)
                    definitions.append(definition)
                if len(catalog_ids) != len(set(catalog_ids)):
                    raise ValueError(f"{path}.items contains duplicate ids.")
                known_ids = set(catalog_ids) | {
                    item_path.stem
                    for item_path in (root / "items").glob("*.json")
                    if item_path.stem not in {
                        "properties",
                        "crafting_purposes",
                        "adventuring_gear",
                    }
                }
                for definition in definitions:
                    missing = {
                        entry.item_id
                        for entry in definition.bundle_contents
                    } - known_ids
                    if missing:
                        raise ValueError(
                            f"item {definition.id} references unknown bundle items: "
                            + ", ".join(sorted(missing))
                        )
                for item_id in catalog_ids:
                    key = ("item", item_id)
                    previous = seen.get(key)
                    if previous is not None:
                        raise ValueError(f"item:{item_id} duplicates {previous}.")
                    seen[key] = path
                    entries.append(_entry(root, path, "item", item_id, header))
                continue
            if kind == "item":
                property_catalog = _load_item_property_catalog(path)
                definition = _parse_item_definition(
                    data,
                    property_catalog,
                    f"item {local_id}",
                )
                for attack in _item_attack_definitions(data):
                    _parse_attack(attack, f"item {definition.id}")
            if kind == "spell":
                definition = _parse_spell_definition(data, local_id)
                collection, effect = _spell_effect_payload(data, definition)
                if collection == "attack":
                    _parse_attack(effect, f"spell {local_id}")
                elif collection == "healing":
                    _parse_healing_source(effect, f"spell {local_id}")
                elif collection == "combat_action":
                    _parse_combat_action(effect, f"spell {local_id}")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(
                _issue(
                    AuditSeverity.ERROR,
                    "definition_invalid",
                    path,
                    str(exc),
                    root,
                )
            )
            continue
        key = (kind, local_id)
        previous = seen.get(key)
        if previous is not None:
            issues.append(
                _issue(
                    AuditSeverity.ERROR,
                    "duplicate_stable_id",
                    path,
                    f"{kind}:{local_id} duplicates {previous}.",
                    root,
                )
            )
            continue
        seen[key] = path
        entries.append(_entry(root, path, kind, local_id, header))
        if kind == "scenario":
            scenario_paths.append(path)

    loaded_scenario_ids: list[str] = []
    for path in scenario_paths:
        try:
            loaded = load_scenario(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            issues.append(
                _issue(
                    AuditSeverity.ERROR,
                    "scenario_reference_or_mechanic_invalid",
                    path,
                    str(exc),
                    root,
                )
            )
            continue
        loaded_scenario_ids.append(loaded.definition.id)

    return ContentAuditReport(
        entries=tuple(sorted(entries, key=lambda entry: entry.stable_id)),
        issues=tuple(issues),
        scenario_ids=tuple(sorted(loaded_scenario_ids)),
    )


def _definition_files(root: Path) -> tuple[tuple[Path, str, str], ...]:
    result: list[tuple[Path, str, str]] = []
    for path in sorted((root / "features").glob("*.json")):
        result.append((path, "feature", "dnd_board_game.feature"))
    for path in sorted((root / "monsters").glob("*.json")):
        result.append((path, "monster", "dnd_board_game.monster"))
    for path in sorted((root / "spells").glob("*.json")):
        result.append((path, "spell", "dnd_board_game.spell"))
    for path in sorted((root / "items").glob("*.json")):
        kind = (
            "item_collection"
            if path.stem == "adventuring_gear"
            else "item_catalog"
            if path.stem in {"properties", "crafting_purposes"}
            else "item"
        )
        schema = (
            "dnd_board_game.item_catalog"
            if kind in {"item_catalog", "item_collection"}
            else "dnd_board_game.item"
        )
        result.append((path, kind, schema))
    for path in sorted((root / "scenarios").glob("*.json")):
        if (path.parent / path.stem / "scenario.json").exists():
            continue
        result.append((path, "scenario", "dnd_board_game.scenario"))
    for path in sorted((root / "scenarios").glob("*/scenario.json")):
        result.append((path, "scenario", "dnd_board_game.scenario"))
    return tuple(result)


def _read_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain an object.")
    return data


def _definition_id(data: dict[str, Any], path: Path, kind: str) -> str:
    if kind in {"item_catalog", "item_collection"}:
        return path.stem
    value = data.get("id")
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path}.id must be a non-empty string.")
    return value


def _entry(
    root: Path,
    path: Path,
    kind: str,
    local_id: str,
    header: ContentHeader,
) -> ContentAuditEntry:
    return ContentAuditEntry(
        stable_id=f"{kind}:{local_id}",
        kind=kind,
        local_id=local_id,
        path=str(path.relative_to(root)),
        schema=header.schema,
        schema_version=header.schema_version,
        ruleset_id=header.ruleset_id,
        source_pack_ids=header.source_pack_ids,
    )


def _issue(
    severity: AuditSeverity,
    code: str,
    path: Path,
    message: str,
    root: Path,
) -> ContentAuditIssue:
    try:
        display_path = str(path.relative_to(root))
    except ValueError:
        display_path = str(path)
    return ContentAuditIssue(severity, code, display_path, message)
