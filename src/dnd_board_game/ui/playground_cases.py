"""Validated, data-driven replay cases for the mechanics playground."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


AUDIT_CASES_PATH = Path(
    "content/scenarios/mechanics_playground/audit_cases.json"
)
ALLOWED_STATUSES = {"pending", "tested_automatically", "skipped"}
ALLOWED_MODULES = {
    "combat_arena",
    "spell_lab",
    "exploration_course",
    "social_lab",
    "rest_station",
}


@dataclass(frozen=True, slots=True)
class PlaygroundAuditCase:
    id: str
    category: str
    subject_id: str
    label: str
    status: str
    module: str
    arena_config: dict[str, object]
    party_requirements: tuple[str, ...]
    manual_steps: tuple[str, ...]
    expected_results: tuple[str, ...]
    automatic_tests: tuple[str, ...]
    notes: str = ""

    def as_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "category": self.category,
            "subject_id": self.subject_id,
            "label": self.label,
            "status": self.status,
            "module": self.module,
            "arena_config": dict(self.arena_config),
            "party_requirements": list(self.party_requirements),
            "manual_steps": list(self.manual_steps),
            "expected_results": list(self.expected_results),
            "automatic_tests": list(self.automatic_tests),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class PlaygroundAuditRegistry:
    inventory: dict[str, int]
    cases: tuple[PlaygroundAuditCase, ...]

    def as_payload(self) -> dict[str, object]:
        tested = sum(
            case.status == "tested_automatically" for case in self.cases
        )
        skipped = sum(case.status == "skipped" for case in self.cases)
        total = int(self.inventory["total"])
        return {
            "inventory": dict(self.inventory),
            "progress": {
                "tested": tested,
                "skipped": skipped,
                "resolved": tested + skipped,
                "total": total,
                "percent": round((tested + skipped) * 100 / total, 1),
            },
            "cases": [case.as_payload() for case in self.cases],
        }


def load_playground_audit_registry(
    path: Path = AUDIT_CASES_PATH,
) -> PlaygroundAuditRegistry:
    data = json.loads(path.read_text(encoding="utf-8"))
    inventory = _inventory(data.get("inventory"))
    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("Arena audit cases must be a list.")
    cases = tuple(_case(raw) for raw in raw_cases)
    ids = tuple(case.id for case in cases)
    if len(ids) != len(set(ids)):
        raise ValueError("Arena audit case ids must be unique.")
    if len(cases) > inventory["total"]:
        raise ValueError("Arena audit contains more cases than inventory items.")
    return PlaygroundAuditRegistry(inventory, cases)


def _inventory(raw: Any) -> dict[str, int]:
    if not isinstance(raw, dict):
        raise ValueError("Arena audit inventory must be an object.")
    inventory = {
        key: int(raw[key])
        for key in (
            "spells",
            "species_features",
            "class_features",
            "cross_cutting_mechanics",
            "total",
        )
    }
    calculated = (
        inventory["spells"]
        + inventory["species_features"]
        + inventory["class_features"]
        + inventory["cross_cutting_mechanics"]
    )
    if calculated != inventory["total"]:
        raise ValueError("Arena audit inventory total is inconsistent.")
    return inventory


def _case(raw: Any) -> PlaygroundAuditCase:
    if not isinstance(raw, dict):
        raise ValueError("Arena audit case must be an object.")
    status = str(raw.get("status", ""))
    module = str(raw.get("module", ""))
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Unsupported Arena audit status: {status}.")
    if module not in ALLOWED_MODULES:
        raise ValueError(f"Unsupported Arena module: {module}.")
    automatic_tests = _strings(raw.get("automatic_tests"), "automatic_tests")
    if status == "tested_automatically" and not automatic_tests:
        raise ValueError(
            f"Tested Arena case {raw.get('id')} requires automatic tests."
        )
    config = raw.get("arena_config")
    if not isinstance(config, dict):
        raise ValueError("Arena audit case requires arena_config.")
    return PlaygroundAuditCase(
        id=_text(raw, "id"),
        category=_text(raw, "category"),
        subject_id=_text(raw, "subject_id"),
        label=_text(raw, "label"),
        status=status,
        module=module,
        arena_config=dict(config),
        party_requirements=_strings(
            raw.get("party_requirements"),
            "party_requirements",
        ),
        manual_steps=_strings(raw.get("manual_steps"), "manual_steps"),
        expected_results=_strings(
            raw.get("expected_results"),
            "expected_results",
        ),
        automatic_tests=automatic_tests,
        notes=str(raw.get("notes", "")).strip(),
    )


def _text(raw: dict[str, Any], key: str) -> str:
    value = str(raw.get(key, "")).strip()
    if not value:
        raise ValueError(f"Arena audit case requires {key}.")
    return value


def _strings(raw: Any, key: str) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise ValueError(f"Arena audit case {key} must be a list.")
    values = tuple(str(value).strip() for value in raw)
    if any(not value for value in values):
        raise ValueError(f"Arena audit case {key} cannot contain blanks.")
    return values
