from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


CORE_RULES_PATH = Path("content/llm/dnd5e_core_rules.json")
GROUNDING_TERMS_PATH = Path("content/llm/freeform_grounding_terms.json")
INTENT_CATALOG_PATH = Path("content/llm/intent_catalog.json")


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


@dataclass(frozen=True, slots=True)
class LlmIntentDefinition:
    id: str
    label: str
    description: str


@dataclass(frozen=True, slots=True)
class LlmIntentCatalog:
    version: int
    intents: tuple[LlmIntentDefinition, ...]

    @property
    def ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.intents)


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


@lru_cache(maxsize=1)
def load_llm_intent_catalog(path: Path = INTENT_CATALOG_PATH) -> LlmIntentCatalog:
    data = _read_json(path)
    intents = data.get("intents", {})
    if not isinstance(intents, dict):
        raise ValueError(f"{path}.intents must be an object.")
    parsed: list[LlmIntentDefinition] = []
    for intent_id, raw_definition in intents.items():
        normalized_intent_id = str(intent_id).strip().lower()
        if not normalized_intent_id:
            raise ValueError(f"{path}.intents contains empty intent id.")
        if not isinstance(raw_definition, dict):
            raise ValueError(f"{path}.intents.{intent_id} must be an object.")
        label = str(raw_definition.get("label", "")).strip()
        description = str(raw_definition.get("description", "")).strip()
        if not label:
            raise ValueError(f"{path}.intents.{intent_id}.label cannot be empty.")
        if not description:
            raise ValueError(f"{path}.intents.{intent_id}.description cannot be empty.")
        parsed.append(LlmIntentDefinition(normalized_intent_id, label, description))
    if not parsed:
        raise ValueError(f"{path}.intents cannot be empty.")
    return LlmIntentCatalog(version=int(data.get("version", 1)), intents=tuple(parsed))


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
