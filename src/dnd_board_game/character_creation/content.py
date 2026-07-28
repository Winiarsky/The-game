"""File-backed adapter for the versioned character-creation catalogue."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dnd_board_game.scenarios.content_contract import (
    parse_content_header,
    validate_stable_id,
)
from dnd_board_game.scenarios.loader import (
    _content_ref_path,
    _inventory_item_from_item_data,
    _load_item_property_catalog,
    _parse_spell_definition,
    _read_content_definition,
    _read_item_definition,
)

from .models import (
    AbilityScoreBonuses,
    BackgroundDefinition,
    CharacterBuildResources,
    CharacterCatalog,
    CharacterLevelDefinition,
    ClassDefinition,
    ClassChoiceGroupDefinition,
    ClassOptionDefinition,
    EquipmentPackage,
    ItemGrant,
    SpeciesDefinition,
    SpeciesInnateSpellDefinition,
    SpeciesVariantDefinition,
    SubclassDefinition,
)


CHARACTER_CATALOG_SCHEMA = "dnd_board_game.character_catalog"
CHARACTER_CATALOG_SCHEMA_VERSION = 1


def load_character_catalog(path: str | Path) -> CharacterCatalog:
    catalog_path = Path(path)
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load character catalog {catalog_path}: {exc}.") from exc
    if not isinstance(raw, dict):
        raise ValueError("Character catalog must contain an object.")
    header = parse_content_header(
        raw,
        expected_schema=CHARACTER_CATALOG_SCHEMA,
        context=str(catalog_path),
    )
    species = tuple(
        _parse_species(entry, f"species[{index}]")
        for index, entry in enumerate(_object_list(raw, "species"))
    )
    classes = tuple(
        _parse_class(entry, f"classes[{index}]")
        for index, entry in enumerate(_object_list(raw, "classes"))
    )
    backgrounds = tuple(
        _parse_background(entry, f"backgrounds[{index}]")
        for index, entry in enumerate(_object_list(raw, "backgrounds"))
    )
    return CharacterCatalog(
        schema_version=header.schema_version,
        species=species,
        classes=classes,
        backgrounds=backgrounds,
    )


def load_character_resources(
    catalog: CharacterCatalog,
    content_root: str | Path,
) -> CharacterBuildResources:
    root = Path(content_root)
    anchor = root / "character_creation" / "catalog.json"
    property_catalog = _load_item_property_catalog(anchor)
    item_ids = tuple(
        dict.fromkeys(
            (
            grant.item_id
            for character_class in catalog.classes
            for package in character_class.equipment_packages
            for grant in package.items
            )
        ).keys()
    )
    background_item_ids = tuple(
        dict.fromkeys(
            (
                item_id
                for background in catalog.backgrounds
                for item_id in (
                    *(grant.item_id for grant in background.equipment),
                    *background.tool_choices,
                )
            )
        ).keys()
    )
    item_ids = tuple(dict.fromkeys((*item_ids, *background_item_ids)))
    inventory_items = []
    for item_id in item_ids:
        item_data = _read_item_definition(anchor, item_id)
        inventory_items.append(
            (
                item_id,
                _inventory_item_from_item_data(
                    item_data,
                    quantity=1,
                    equipped=False,
                    source_ref=item_id,
                    property_catalog=property_catalog,
                ),
            )
        )
    spell_ids = tuple(
        dict.fromkeys(
            (
                *(
                    spell_id
                    for species in catalog.species
                    for spell_id in (
                        *species.cantrip_choices,
                        *species.fixed_cantrip_ids,
                        *(
                            spell.spell_id
                            for spell in species.innate_spells
                        ),
                    )
                ),
                *(
                    spell_id
                    for character_class in catalog.classes
                    for spell_id in (
                        *character_class.cantrip_choices,
                        *character_class.spell_choices,
                        *(
                            spell_id
                            for subclass in character_class.subclass_choices
                            for spell_id in (
                                *subclass.always_prepared_spell_ids,
                                *subclass.additional_spell_choice_ids,
                                *(
                                    spell_id
                                    for entry in subclass.level_progression
                                    for spell_id in (
                                        *entry.always_prepared_spell_ids,
                                        *entry.additional_spell_choice_ids,
                                    )
                                ),
                            )
                        ),
                        *(
                            spell_id
                            for group in character_class.choice_groups
                            for option in group.options
                            for spell_id in (
                                *option.always_prepared_spell_ids,
                                *(
                                    spell_id
                                    for entry in option.level_progression
                                    for spell_id in entry.always_prepared_spell_ids
                                ),
                            )
                        ),
                    )
                ),
            )
        )
    )
    spells = []
    for spell_id in spell_ids:
        spell_data = _read_content_definition(
            _content_ref_path(anchor, "spells", spell_id),
            "dnd_board_game.spell",
        )
        spells.append((spell_id, _parse_spell_definition(spell_data, spell_id)))
    return CharacterBuildResources(tuple(inventory_items), tuple(spells))


def _parse_species(data: dict[str, Any], field: str) -> SpeciesDefinition:
    definition_id = _definition_id(data, field)
    bonuses = _mapping(data.get("ability_bonuses", {}), f"{field}.ability_bonuses")
    return SpeciesDefinition(
        id=definition_id,
        name=_required_text(data, "name", field),
        speed_feet=int(data.get("speed_feet", 30)),
        description=str(data.get("description", "")).strip(),
        size=str(data.get("size", "medium")),
        ability_bonuses=AbilityScoreBonuses(
            strength=int(bonuses.get("strength", 0)),
            dexterity=int(bonuses.get("dexterity", 0)),
            constitution=int(bonuses.get("constitution", 0)),
            intelligence=int(bonuses.get("intelligence", 0)),
            wisdom=int(bonuses.get("wisdom", 0)),
            charisma=int(bonuses.get("charisma", 0)),
        ),
        darkvision_feet=int(data.get("darkvision_feet", 0)),
        skill_proficiencies=_string_tuple(data.get("skill_proficiencies", []), field),
        weapon_proficiencies=_string_tuple(data.get("weapon_proficiencies", []), field),
        tool_proficiencies=_string_tuple(data.get("tool_proficiencies", []), field),
        languages=_string_tuple(data.get("languages", []), field),
        trait_ids=_string_tuple(data.get("trait_ids", []), field),
        ability_bonus_choice_count=int(data.get("ability_bonus_choice_count", 0)),
        ability_bonus_choice_value=int(data.get("ability_bonus_choice_value", 1)),
        ability_bonus_choice_exclusions=_string_tuple(
            data.get("ability_bonus_choice_exclusions", []),
            field,
        ),
        skill_choice_count=int(data.get("skill_choice_count", 0)),
        skill_choices=_string_tuple(data.get("skill_choices", []), field),
        tool_choice_count=int(data.get("tool_choice_count", 0)),
        tool_choices=_string_tuple(data.get("tool_choices", []), field),
        language_choice_count=int(data.get("language_choice_count", 0)),
        variant_choice_count=int(data.get("variant_choice_count", 0)),
        variant_choices=tuple(
            SpeciesVariantDefinition(
                id=_definition_id(entry, f"{field}.variant_choices[{index}]"),
                name=_required_text(
                    entry,
                    "name",
                    f"{field}.variant_choices[{index}]",
                ),
                trait_ids=_string_tuple(
                    entry.get("trait_ids", []),
                    f"{field}.variant_choices[{index}].trait_ids",
                ),
            )
            for index, entry in enumerate(
                _object_list(data, "variant_choices", context=field, default=[])
            )
        ),
        cantrip_choice_count=int(data.get("cantrip_choice_count", 0)),
        cantrip_choices=_string_tuple(data.get("cantrip_choices", []), field),
        fixed_cantrip_ids=_string_tuple(
            data.get("fixed_cantrip_ids", []),
            field,
        ),
        innate_spells=tuple(
            SpeciesInnateSpellDefinition(
                spell_id=_required_text(
                    entry,
                    "spell_id",
                    f"{field}.innate_spells[{index}]",
                ),
                level=int(entry.get("level", 1)),
                resource_id=_required_text(
                    entry,
                    "resource_id",
                    f"{field}.innate_spells[{index}]",
                ),
                recovery=str(entry.get("recovery", "long_rest")),
            )
            for index, entry in enumerate(
                _object_list(
                    data,
                    "innate_spells",
                    context=field,
                    default=[],
                )
            )
        ),
        cantrip_ability=(
            str(data["cantrip_ability"])
            if data.get("cantrip_ability") is not None
            else None
        ),
    )


def _parse_class(data: dict[str, Any], field: str) -> ClassDefinition:
    packages = tuple(
        EquipmentPackage(
            id=_definition_id(package, f"{field}.equipment_packages[{index}]"),
            label=_required_text(package, "label", f"{field}.equipment_packages[{index}]"),
            items=tuple(
                _parse_item_grant(item, f"{field}.equipment_packages[{index}].items[{item_index}]")
                for item_index, item in enumerate(
                    _object_list(package, "items", context=f"{field}.equipment_packages[{index}]")
                )
            ),
        )
        for index, package in enumerate(_object_list(data, "equipment_packages", context=field))
    )
    spell_slots = _mapping(data.get("spell_slots", {}), f"{field}.spell_slots")
    subclasses = tuple(
        SubclassDefinition(
            id=_definition_id(entry, f"{field}.subclass_choices[{index}]"),
            name=_required_text(entry, "name", f"{field}.subclass_choices[{index}]"),
            feature_ids=_string_tuple(entry.get("feature_ids", []), field),
            armor_proficiencies=_string_tuple(
                entry.get("armor_proficiencies", []),
                field,
            ),
            weapon_proficiencies=_string_tuple(
                entry.get("weapon_proficiencies", []),
                field,
            ),
            always_prepared_spell_ids=_string_tuple(
                entry.get("always_prepared_spell_ids", []),
                field,
            ),
            additional_spell_choice_ids=_string_tuple(
                entry.get("additional_spell_choice_ids", []),
                field,
            ),
            level_progression=_parse_level_progression(
                entry.get("level_progression", []),
                f"{field}.subclass_choices[{index}].level_progression",
            ),
        )
        for index, entry in enumerate(
            _object_list(data, "subclass_choices", context=field, default=[])
        )
    )
    return ClassDefinition(
        id=_definition_id(data, field),
        name=_required_text(data, "name", field),
        hit_die=int(data["hit_die"]),
        saving_throw_proficiencies=_string_tuple(data.get("saving_throw_proficiencies", []), field),
        skill_choice_count=int(data.get("skill_choice_count", 0)),
        skill_choices=_string_tuple(data.get("skill_choices", []), field),
        description=str(data.get("description", "")).strip(),
        weapon_proficiencies=_string_tuple(data.get("weapon_proficiencies", []), field),
        armor_proficiencies=_string_tuple(data.get("armor_proficiencies", []), field),
        tool_proficiencies=_string_tuple(data.get("tool_proficiencies", []), field),
        equipment_packages=packages,
        feature_ids=_string_tuple(data.get("feature_ids", []), field),
        fighting_style_choices=_string_tuple(
            data.get("fighting_style_choices", []),
            field,
        ),
        fighting_style_choice_level=int(data.get("fighting_style_choice_level", 1)),
        expertise_choice_count=int(data.get("expertise_choice_count", 0)),
        expertise_choice_level=int(data.get("expertise_choice_level", 1)),
        spellcasting_ability=(
            str(data["spellcasting_ability"])
            if data.get("spellcasting_ability") is not None
            else None
        ),
        spellcasting_level=int(data.get("spellcasting_level", 1)),
        cantrip_choice_count=int(data.get("cantrip_choice_count", 0)),
        cantrip_choices=_string_tuple(data.get("cantrip_choices", []), field),
        spell_choice_count=int(data.get("spell_choice_count", 0)),
        spell_choices=_string_tuple(data.get("spell_choices", []), field),
        spell_slots=tuple(
            (int(level), int(count)) for level, count in spell_slots.items()
        ),
        spell_slot_recovery=str(data.get("spell_slot_recovery", "long_rest")),
        preparation_kind=str(data.get("preparation_kind", "")),
        preparation_formula=str(data.get("preparation_formula", "")),
        subclass_choice_count=int(data.get("subclass_choice_count", 0)),
        subclass_choice_level=int(data.get("subclass_choice_level", 1)),
        subclass_choices=subclasses,
        level_progression=_parse_level_progression(
            data.get("level_progression", []),
            f"{field}.level_progression",
        ),
        choice_groups=tuple(
            ClassChoiceGroupDefinition(
                id=_definition_id(entry, f"{field}.choice_groups[{index}]"),
                name=_required_text(
                    entry,
                    "name",
                    f"{field}.choice_groups[{index}]",
                ),
                level=int(entry.get("level", 1)),
                choice_count=int(entry.get("choice_count", 1)),
                requires_option_id=str(
                    entry.get("requires_option_id", "")
                ).strip(),
                options=tuple(
                    ClassOptionDefinition(
                        id=_definition_id(
                            option,
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        name=_required_text(
                            option,
                            "name",
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        feature_ids=_string_tuple(
                            option.get("feature_ids", []),
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        tool_proficiencies=_string_tuple(
                            option.get("tool_proficiencies", []),
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        skill_proficiencies=_string_tuple(
                            option.get("skill_proficiencies", []),
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        languages=_string_tuple(
                            option.get("languages", []),
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        always_prepared_spell_ids=_string_tuple(
                            option.get("always_prepared_spell_ids", []),
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        at_will_spell_ids=_string_tuple(
                            option.get("at_will_spell_ids", []),
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        ritual_spell_ids=_string_tuple(
                            option.get("ritual_spell_ids", []),
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        cantrip_choice_count=int(
                            option.get("cantrip_choice_count", 0)
                        ),
                        cantrip_choices=_string_tuple(
                            option.get("cantrip_choices", []),
                            f"{field}.choice_groups[{index}].options[{option_index}]",
                        ),
                        level_progression=_parse_level_progression(
                            option.get("level_progression", []),
                            f"{field}.choice_groups[{index}].options[{option_index}].level_progression",
                        ),
                    )
                    for option_index, option in enumerate(
                        _object_list(
                            entry,
                            "options",
                            context=f"{field}.choice_groups[{index}]",
                        )
                    )
                ),
            )
            for index, entry in enumerate(
                _object_list(data, "choice_groups", context=field, default=[])
            )
        ),
    )


def _parse_level_progression(
    raw: object,
    field: str,
) -> tuple[CharacterLevelDefinition, ...]:
    entries = _object_list({"entries": raw}, "entries", context=field)
    return tuple(
        CharacterLevelDefinition(
            level=_required_int(entry, "level", f"{field}[{index}]"),
            feature_ids=_string_tuple(
                entry.get("feature_ids", []),
                f"{field}[{index}].feature_ids",
            ),
            spell_slots=tuple(
                sorted(
                    (
                        int(level),
                        int(count),
                    )
                    for level, count in _mapping(
                        entry.get("spell_slots", {}),
                        f"{field}[{index}].spell_slots",
                    ).items()
                )
            ),
            cantrip_choice_count=(
                int(entry["cantrip_choice_count"])
                if "cantrip_choice_count" in entry
                else None
            ),
            spell_choice_count=(
                int(entry["spell_choice_count"])
                if "spell_choice_count" in entry
                else None
            ),
            always_prepared_spell_ids=_string_tuple(
                entry.get("always_prepared_spell_ids", []),
                f"{field}[{index}].always_prepared_spell_ids",
            ),
            additional_spell_choice_ids=_string_tuple(
                entry.get("additional_spell_choice_ids", []),
                f"{field}[{index}].additional_spell_choice_ids",
            ),
        )
        for index, entry in enumerate(entries)
    )


def _parse_background(data: dict[str, Any], field: str) -> BackgroundDefinition:
    return BackgroundDefinition(
        id=_definition_id(data, field),
        name=_required_text(data, "name", field),
        description=str(data.get("description", "")).strip(),
        skill_proficiencies=_string_tuple(data.get("skill_proficiencies", []), field),
        tool_proficiencies=_string_tuple(data.get("tool_proficiencies", []), field),
        languages=_string_tuple(data.get("languages", []), field),
        tool_choice_count=int(data.get("tool_choice_count", 0)),
        tool_choices=_string_tuple(data.get("tool_choices", []), field),
        language_choice_count=int(data.get("language_choice_count", 0)),
        equipment=tuple(
            _parse_item_grant(item, f"{field}.equipment[{index}]")
            for index, item in enumerate(_object_list(data, "equipment", context=field))
        ),
        starting_gp=int(data.get("starting_gp", 0)),
        feature_ids=_string_tuple(data.get("feature_ids", []), field),
        permission_ids=_string_tuple(data.get("permission_ids", []), field),
    )


def _parse_item_grant(data: dict[str, Any], field: str) -> ItemGrant:
    return ItemGrant(
        item_id=_required_text(data, "item_id", field),
        quantity=int(data.get("quantity", 1)),
        equipped=bool(data.get("equipped", False)),
        separate_instances=bool(data.get("separate_instances", False)),
    )


def _object_list(
    data: dict[str, Any],
    key: str,
    *,
    context: str = "character catalog",
    default: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    value = data.get(key, default)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{context}.{key} must be a list of objects.")
    return value


def _mapping(value: object, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be an object.")
    return value


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must contain a list of non-empty strings.")
    result = tuple(value)
    if len(result) != len(set(result)):
        raise ValueError(f"{field} cannot contain duplicate ids.")
    return result


def _definition_id(data: dict[str, Any], field: str) -> str:
    return validate_stable_id(_required_text(data, "id", field), f"{field}.id")


def _required_text(data: dict[str, Any], key: str, field: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field}.{key} must be a non-empty string.")
    return value.strip()


def _required_int(data: dict[str, Any], key: str, field: str) -> int:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field}.{key} must be an integer.")
    return value
