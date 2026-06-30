from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


CORE_RULES_PATH = Path("content/llm/dnd5e_core_rules.json")
GROUNDING_TERMS_PATH = Path("content/llm/freeform_grounding_terms.json")


@dataclass(frozen=True, slots=True)
class LlmCoreRules:
    abilities: tuple[str, ...]
    skills: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GuardedResourceMention:
    label: str
    variants: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FreeformGroundingTerms:
    guarded_resource_mentions: tuple[GuardedResourceMention, ...]


@lru_cache(maxsize=1)
def load_llm_core_rules(path: Path = CORE_RULES_PATH) -> LlmCoreRules:
    data = _read_json(path)
    return LlmCoreRules(
        abilities=_string_tuple(data.get("abilities", ()), f"{path}.abilities"),
        skills=_string_tuple(data.get("skills", ()), f"{path}.skills"),
    )


@lru_cache(maxsize=1)
def load_freeform_grounding_terms(path: Path = GROUNDING_TERMS_PATH) -> FreeformGroundingTerms:
    data = _read_json(path)
    entries = data.get("guarded_resource_mentions", [])
    if not isinstance(entries, list):
        raise ValueError(f"{path}.guarded_resource_mentions must be a list.")
    return FreeformGroundingTerms(
        guarded_resource_mentions=tuple(_parse_guarded_resource_mention(entry, path) for entry in entries)
    )


def _parse_guarded_resource_mention(data: Any, path: Path) -> GuardedResourceMention:
    if not isinstance(data, dict):
        raise ValueError(f"{path}.guarded_resource_mentions entries must be objects.")
    label = str(data.get("label", "")).strip()
    if not label:
        raise ValueError(f"{path}.guarded_resource_mentions entry is missing label.")
    variants = _string_tuple(data.get("variants", ()), f"{path}.guarded_resource_mentions.{label}.variants")
    if not variants:
        raise ValueError(f"{path}.guarded_resource_mentions.{label}.variants cannot be empty.")
    return GuardedResourceMention(label, variants)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return data


def _string_tuple(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list | tuple):
        raise ValueError(f"{field} must be a list.")
    result = tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))
    return result
