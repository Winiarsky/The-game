"""Versioned saved-character document based on player choices."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from dnd_board_game.actors import AbilityScores

from .builder import build_character
from .models import (
    ABILITY_IDS,
    CHARACTER_RECORD_SCHEMA_VERSION,
    CharacterBuildResources,
    CharacterCatalog,
    CharacterDraft,
    CreatedCharacter,
)


CHARACTER_RECORD_SCHEMA = "dnd_board_game.character"
CHARACTER_RULESET_ID = "dnd_5e_2014"


def character_record_payload(character: CreatedCharacter) -> dict[str, object]:
    actor = character.actor
    return {
        "schema": CHARACTER_RECORD_SCHEMA,
        "schema_version": character.schema_version,
        "ruleset_id": CHARACTER_RULESET_ID,
        "id": str(actor.id),
        "name": actor.name,
        "level": actor.level,
        "experience_points": actor.experience_points,
        "species_id": character.species_id,
        "class_id": character.class_id,
        "background_id": character.background_id,
        "base_ability_scores": {
            ability: getattr(character.base_ability_scores, ability)
            for ability in ABILITY_IDS
        },
        "selected_skill_ids": list(character.selected_skill_ids),
        "selected_expertise_ids": list(character.selected_expertise_ids),
        "selected_fighting_style_id": character.selected_fighting_style_id,
        "equipment_package_id": character.equipment_package_id,
        "selected_cantrip_ids": list(character.selected_cantrip_ids),
        "selected_spell_ids": list(character.selected_spell_ids),
        "selected_prepared_spell_ids": list(character.selected_prepared_spell_ids),
        "selected_subclass_id": character.selected_subclass_id,
        "selected_species_bonus_ability_ids": list(
            character.selected_species_bonus_ability_ids
        ),
        "selected_species_skill_ids": list(character.selected_species_skill_ids),
        "selected_species_tool_ids": list(character.selected_species_tool_ids),
        "selected_species_language_ids": list(
            character.selected_species_language_ids
        ),
        "selected_species_variant_id": character.selected_species_variant_id,
        "selected_species_cantrip_ids": list(
            character.selected_species_cantrip_ids
        ),
        "selected_class_option_ids": list(character.selected_class_option_ids),
        "selected_background_tool_ids": list(
            character.selected_background_tool_ids
        ),
        "selected_background_language_ids": list(
            character.selected_background_language_ids
        ),
        "portrait": actor.portrait,
    }


def created_character_from_payload(
    raw: object,
    catalog: CharacterCatalog,
    resources: CharacterBuildResources,
) -> CreatedCharacter:
    if not isinstance(raw, dict):
        raise ValueError("Zapis postaci musi być obiektem.")
    if raw.get("schema") != CHARACTER_RECORD_SCHEMA:
        raise ValueError("Nieznany format zapisu postaci.")
    raw = _migrate_character_record(raw)
    if raw.get("schema_version") != CHARACTER_RECORD_SCHEMA_VERSION:
        raise ValueError("Nieobsługiwana wersja zapisu postaci.")
    if raw.get("ruleset_id") != CHARACTER_RULESET_ID:
        raise ValueError("Zapis postaci korzysta z innego rulesetu.")
    abilities = _mapping(raw.get("base_ability_scores"), "base_ability_scores")
    draft = CharacterDraft(
        id=_text(raw, "id"),
        name=_text(raw, "name"),
        level=_integer(raw, "level"),
        species_id=_text(raw, "species_id"),
        class_id=_text(raw, "class_id"),
        background_id=_text(raw, "background_id"),
        base_ability_scores=AbilityScores(
            **{
                ability: _integer(abilities, ability)
                for ability in ABILITY_IDS
            }
        ),
        selected_skill_ids=_strings(raw, "selected_skill_ids"),
        selected_expertise_ids=_strings(
            raw,
            "selected_expertise_ids",
            default=(),
        ),
        selected_fighting_style_id=str(
            raw.get("selected_fighting_style_id", "")
        ).strip(),
        equipment_package_id=_text(raw, "equipment_package_id"),
        selected_cantrip_ids=_strings(raw, "selected_cantrip_ids"),
        selected_spell_ids=_strings(raw, "selected_spell_ids"),
        selected_prepared_spell_ids=_strings(raw, "selected_prepared_spell_ids"),
        selected_subclass_id=str(raw.get("selected_subclass_id", "")).strip(),
        portrait=str(raw.get("portrait", "")).strip(),
        selected_species_bonus_ability_ids=_strings(
            raw,
            "selected_species_bonus_ability_ids",
            default=(),
        ),
        selected_species_skill_ids=_strings(
            raw,
            "selected_species_skill_ids",
            default=(),
        ),
        selected_species_tool_ids=_strings(
            raw,
            "selected_species_tool_ids",
            default=(),
        ),
        selected_species_language_ids=_strings(
            raw,
            "selected_species_language_ids",
            default=(),
        ),
        selected_species_variant_id=str(
            raw.get("selected_species_variant_id", "")
        ).strip(),
        selected_species_cantrip_ids=_strings(
            raw,
            "selected_species_cantrip_ids",
            default=(),
        ),
        selected_class_option_ids=_strings(
            raw,
            "selected_class_option_ids",
            default=(),
        ),
        selected_background_tool_ids=_strings(
            raw,
            "selected_background_tool_ids",
            default=(),
        ),
        selected_background_language_ids=_strings(
            raw,
            "selected_background_language_ids",
            default=(),
        ),
    )
    character = build_character(draft, catalog, resources)
    experience_points = _integer(raw, "experience_points")
    if experience_points < 0:
        raise ValueError("experience_points nie może być ujemne.")
    return replace(
        character,
        actor=replace(
            character.actor,
            experience_points=experience_points,
        ),
    )


def _migrate_character_record(raw: dict[str, Any]) -> dict[str, Any]:
    version = raw.get("schema_version")
    if version == 2:
        raw = {
            **raw,
            "schema_version": 3,
            "experience_points": 0,
        }
        version = 3
    if version == 3:
        raw = {
            **raw,
            "schema_version": 4,
            "selected_species_bonus_ability_ids": [],
        }
        version = 4
    if version == 4:
        species_id = str(raw.get("species_id", ""))
        raw = {
            **raw,
            "schema_version": 5,
            "selected_species_skill_ids": (
                ["arcana", "nature"] if species_id == "half_elf" else []
            ),
            "selected_species_tool_ids": (
                ["smiths_tools"] if species_id == "dwarf" else []
            ),
            "selected_species_language_ids": (
                ["dwarvish"]
                if species_id in {"human", "elf", "half_elf"}
                else []
            ),
            "selected_species_variant_id": (
                "red_dragon_ancestry" if species_id == "dragonborn" else ""
            ),
            "selected_species_cantrip_ids": [],
        }
        version = 5
    if version == 5:
        raw = {
            **raw,
            "schema_version": 6,
            "selected_class_option_ids": [],
        }
        version = 6
    if version == 6:
        background_id = str(raw.get("background_id", ""))
        species_id = str(raw.get("species_id", ""))
        known_languages = {
            "common",
            *(
                raw.get("selected_species_language_ids", [])
                if isinstance(raw.get("selected_species_language_ids"), list)
                else []
            ),
        }
        known_languages.update(
            {
                "elf": "elvish",
                "dwarf": "dwarvish",
                "halfling": "halfling",
                "dragonborn": "draconic",
                "gnome": "gnomish",
                "half_elf": "elvish",
                "half_orc": "orc",
                "tiefling": "infernal",
            }.get(species_id, "")
            for _ in (0,)
        )
        compatible_languages = [
            language
            for language in ("elvish", "dwarvish", "gnomish", "orc")
            if language not in known_languages
        ][:2]
        return {
            **raw,
            "schema_version": 7,
            "selected_background_tool_ids": (
                ["dice_set"]
                if background_id in {"soldier", "criminal"}
                else []
            ),
            "selected_background_language_ids": (
                compatible_languages
                if background_id in {"acolyte", "sage"}
                else []
            ),
        }
    return raw


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} musi być obiektem.")
    return value


def _text(data: dict[str, Any], field: str) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} musi być niepustym tekstem.")
    return value.strip()


def _integer(data: dict[str, Any], field: str) -> int:
    value = data.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{field} musi być liczbą całkowitą.")
    return value


def _strings(
    data: dict[str, Any],
    field: str,
    *,
    default: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    value = data.get(field, list(default) if default is not None else None)
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{field} musi być listą niepustych identyfikatorów.")
    return tuple(value)
