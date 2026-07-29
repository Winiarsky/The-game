"""Pure validation and Actor construction for level-1 single-class characters."""

from __future__ import annotations

from dataclasses import replace
import re

from dnd_board_game.actors import (
    AbilityScores,
    Actor,
    ActorId,
    ActorResourcePool,
    ActorSenseProfile,
    DamageAffinityProfile,
    Faction,
    FeatureGrant,
    FeatureSourceKind,
    CreatureSize,
    HitDicePool,
    ProficiencyProfile,
    RecoveryPeriod,
)
from dnd_board_game.actors.spell_preparation import (
    PreparableSpell,
    SpellPreparationProfile,
)
from dnd_board_game.combat import SpellSlotState
from dnd_board_game.combat import DamageType
from dnd_board_game.core.player_labels_pl import player_label
from dnd_board_game.inventory import (
    CurrencyWallet,
    InventoryItem,
    normalize_hand_equipment,
)
from dnd_board_game.rules import (
    SpellAccessKind,
    SpellAccessProfile,
    SpellDefinition,
    ability_modifier,
)
from dnd_board_game.world import Coordinate

from .models import (
    ABILITY_IDS,
    CHARACTER_RECORD_SCHEMA_VERSION,
    CharacterBuildResources,
    CharacterCatalog,
    CharacterDraft,
    CharacterValidation,
    CharacterValidationIssue,
    ClassDefinition,
    ClassOptionDefinition,
    CreatedCharacter,
    ItemGrant,
)
from .point_buy import POINT_BUY_BUDGET, POINT_BUY_MAXIMUM, POINT_BUY_MINIMUM, summarize_point_buy


_STABLE_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_LANGUAGE_IDS = frozenset(
    {
        "common",
        "dwarvish",
        "elvish",
        "giant",
        "gnomish",
        "goblin",
        "halfling",
        "orc",
        "abyssal",
        "celestial",
        "deep_speech",
        "draconic",
        "infernal",
        "primordial",
        "sylvan",
        "undercommon",
    }
)


def validate_character_draft(
    draft: CharacterDraft,
    catalog: CharacterCatalog,
) -> CharacterValidation:
    issues: list[CharacterValidationIssue] = []
    if not _STABLE_ID.fullmatch(draft.id):
        issues.append(_issue("id", "invalid_id", "Id postaci musi być stabilnym identyfikatorem snake_case."))
    if not draft.name.strip():
        issues.append(_issue("name", "required", "Postać musi mieć imię."))
    if not 1 <= draft.level <= 3:
        issues.append(_issue("level", "unsupported", "Ten kreator obsługuje poziomy od 1 do 3."))
    species = catalog.species_by_id(draft.species_id)
    character_class = catalog.class_by_id(draft.class_id)
    background = catalog.background_by_id(draft.background_id)
    if species is None:
        issues.append(_issue("species_id", "unknown", "Wybierz dostępną species."))
    else:
        selected_bonus_abilities = draft.selected_species_bonus_ability_ids
        if len(selected_bonus_abilities) != len(set(selected_bonus_abilities)):
            issues.append(
                _issue(
                    "selected_species_bonus_ability_ids",
                    "duplicates",
                    "Każdą premiowaną cechę można wybrać tylko raz.",
                )
            )
        if len(selected_bonus_abilities) != species.ability_bonus_choice_count:
            issues.append(
                _issue(
                    "selected_species_bonus_ability_ids",
                    "wrong_count",
                    f"Wybierz dokładnie {species.ability_bonus_choice_count} "
                    "dodatkowych cech species.",
                )
            )
        allowed = set(ABILITY_IDS) - set(species.ability_bonus_choice_exclusions)
        if set(selected_bonus_abilities) - allowed:
            issues.append(
                _issue(
                    "selected_species_bonus_ability_ids",
                    "unknown",
                    "Wybrano niedozwoloną dodatkową cechę species.",
                )
            )
        issues.extend(_validate_species_choices(draft, species))
    if character_class is None:
        issues.append(_issue("class_id", "unknown", "Wybierz dostępną klasę."))
    if background is None:
        issues.append(_issue("background_id", "unknown", "Wybierz dostępny background."))
    else:
        issues.extend(_validate_background_choices(draft, background, species))
    point_buy = summarize_point_buy(draft.base_ability_scores)
    if not point_buy.scores_in_range:
        issues.append(
            _issue(
                "base_ability_scores",
                "point_buy_range",
                f"Każda bazowa cecha musi mieścić się między "
                f"{POINT_BUY_MINIMUM} a {POINT_BUY_MAXIMUM}.",
            )
        )
    elif point_buy.remaining != 0:
        balance = (
            f"pozostało: {point_buy.remaining}"
            if point_buy.remaining > 0
            else f"przekroczono pulę o {-point_buy.remaining}"
        )
        issues.append(
            _issue(
                "base_ability_scores",
                "incomplete_point_buy",
                f"Rozdaj pełną pulę {POINT_BUY_BUDGET} punktów point buy "
                f"({balance}).",
            )
        )
    if len(draft.selected_skill_ids) != len(set(draft.selected_skill_ids)):
        issues.append(_issue("selected_skill_ids", "duplicates", "Nie można wybrać tej samej umiejętności dwa razy."))
    if len(draft.selected_cantrip_ids) != len(set(draft.selected_cantrip_ids)):
        issues.append(_issue("selected_cantrip_ids", "duplicates", "Nie można wybrać tego samego cantripu dwa razy."))
    if len(draft.selected_spell_ids) != len(set(draft.selected_spell_ids)):
        issues.append(_issue("selected_spell_ids", "duplicates", "Nie można wybrać tego samego czaru dwa razy."))
    if len(draft.selected_prepared_spell_ids) != len(set(draft.selected_prepared_spell_ids)):
        issues.append(
            _issue(
                "selected_prepared_spell_ids",
                "duplicates",
                "Nie można przygotować tego samego czaru dwa razy.",
            )
        )
    if len(draft.selected_expertise_ids) != len(set(draft.selected_expertise_ids)):
        issues.append(_issue("selected_expertise_ids", "duplicates", "Nie można wybrać tej samej Expertise dwa razy."))
    if character_class is not None:
        issues.extend(
            _validate_class_choices(
                draft,
                character_class,
                species,
                background,
            )
        )
    return CharacterValidation(tuple(issues))


def build_character(
    draft: CharacterDraft,
    catalog: CharacterCatalog,
    resources: CharacterBuildResources,
) -> CreatedCharacter:
    validation = validate_character_draft(draft, catalog)
    if not validation.valid:
        raise ValueError("; ".join(issue.message for issue in validation.issues))
    species = catalog.species_by_id(draft.species_id)
    character_class = catalog.class_by_id(draft.class_id)
    background = catalog.background_by_id(draft.background_id)
    assert species is not None and character_class is not None and background is not None
    subclass = next(
        (
            item
            for item in character_class.subclass_choices
            if item.id == draft.selected_subclass_id
        ),
        None,
    )
    species_variant = next(
        (
            item
            for item in species.variant_choices
            if item.id == draft.selected_species_variant_id
        ),
        None,
    )
    species_trait_ids = _unique(
        (
            *species.trait_ids,
            *(species_variant.trait_ids if species_variant is not None else ()),
        )
    )
    class_options = _selected_class_options(
        character_class,
        draft.selected_class_option_ids,
    )
    class_option_feature_ids = _unique(
        tuple(
            feature_id
            for option in class_options
            for feature_id in option.feature_ids
        )
    )

    package = next(
        item for item in character_class.equipment_packages if item.id == draft.equipment_package_id
    )
    selected_background_tools = tuple(
        ItemGrant(tool_id)
        for tool_id in draft.selected_background_tool_ids
        if resources.inventory_item(tool_id) is not None
    )
    item_refs = _merge_item_grants(
        (
            *package.items,
            *background.equipment,
            *selected_background_tools,
        )
    )
    inventory = _build_inventory(item_refs, resources)
    class_spell_ids = (
        character_class.spell_choices
        if character_class.preparation_kind == SpellAccessKind.PREPARED.value
        else draft.selected_spell_ids
    )
    always_prepared_spell_ids = _unique(
        (
            *(
                _progressive_always_prepared_spells(subclass, draft.level)
                if subclass is not None
                else ()
            ),
            *(
                spell_id
                for option in class_options
                for spell_id in _progressive_always_prepared_spells(
                    option,
                    draft.level,
                )
            ),
        )
    )
    spells = _build_spells(
        _unique(
            (
                *draft.selected_cantrip_ids,
                *draft.selected_species_cantrip_ids,
                *species.fixed_cantrip_ids,
                *(
                    innate.spell_id
                    for innate in species.innate_spells
                    if innate.level <= draft.level
                ),
                *class_spell_ids,
                *always_prepared_spell_ids,
                *(
                    spell_id
                    for option in class_options
                    for spell_id in option.at_will_spell_ids
                ),
                *(
                    spell_id
                    for option in class_options
                    for spell_id in option.ritual_spell_ids
                ),
            )
        ),
        resources,
    )
    maximum_spell_level = max(
        (spell_level for spell_level, _ in _spell_slots_at_level(
            character_class,
            draft.level,
        )),
        default=0,
    )
    illegal_selected_spells = tuple(
        spell.name
        for spell in spells
        if spell.id in draft.selected_spell_ids
        and spell.level > maximum_spell_level
    )
    if illegal_selected_spells:
        raise ValueError(
            "Poziom postaci nie pozwala jeszcze wybrać czarów: "
            f"{', '.join(illegal_selected_spells)}."
        )
    innate_spell_ids = {
        definition.spell_id
        for definition in species.innate_spells
        if definition.level <= draft.level
    }
    spells = tuple(
        spell
        for spell in spells
        if (
            spell.level == 0
            or spell.level <= maximum_spell_level
            or spell.id in innate_spell_ids
        )
    )
    scores = _apply_species_ability_bonuses(
        species,
        draft.base_ability_scores,
        draft.selected_species_bonus_ability_ids,
    )
    skills = _unique(
        (
            *species.skill_proficiencies,
            *draft.selected_species_skill_ids,
            *background.skill_proficiencies,
            *draft.selected_skill_ids,
            *(
                skill_id
                for option in class_options
                for skill_id in option.skill_proficiencies
            ),
        )
    )
    proficiencies = ProficiencyProfile(
        saving_throws=character_class.saving_throw_proficiencies,
        skills=skills,
        expertise=draft.selected_expertise_ids,
        weapons=_unique(
            (
                "unarmed_strike",
                *species.weapon_proficiencies,
                *character_class.weapon_proficiencies,
                *(subclass.weapon_proficiencies if subclass is not None else ()),
            )
        ),
        armor=_unique(
            (
                *character_class.armor_proficiencies,
                *(subclass.armor_proficiencies if subclass is not None else ()),
            )
        ),
        tools=_unique(
            (
                *species.tool_proficiencies,
                *draft.selected_species_tool_ids,
                *background.tool_proficiencies,
                *draft.selected_background_tool_ids,
                *character_class.tool_proficiencies,
                *(
                    tool_id
                    for option in class_options
                    for tool_id in option.tool_proficiencies
                ),
            )
        ),
    )
    constitution_modifier = ability_modifier(scores.constitution)
    max_hp = max(1, character_class.hit_die + constitution_modifier)
    fixed_hit_point_gain = character_class.hit_die // 2 + 1
    for _level in range(2, draft.level + 1):
        max_hp += max(1, fixed_hit_point_gain + constitution_modifier)
    if "dwarven_toughness" in species_trait_ids:
        max_hp += draft.level
    if (
        subclass is not None
        and "draconic_resilience"
        in _subclass_feature_ids(subclass, draft.level)
    ):
        max_hp += draft.level
    spell_save_dc = (
        8 + 2 + ability_modifier(getattr(scores, character_class.spellcasting_ability))
        if character_class.spellcasting_ability is not None
        else 0
    )
    spell_access, spell_preparation = _spell_profiles(
        character_class,
        draft,
        spells,
        scores,
        always_prepared_spell_ids,
        level=draft.level,
    )
    spell_access = (
        *spell_access,
        *_class_option_spell_access(
            character_class,
            class_options,
        ),
        *_species_spell_access(species, draft),
    )
    actor = Actor(
        id=ActorId(draft.id),
        name=draft.name.strip(),
        ac=_unarmored_armor_class(
            scores,
            _class_feature_ids(character_class, draft.level),
            (
                _subclass_feature_ids(subclass, draft.level)
                if subclass is not None
                else ()
            ),
        ),
        hp=max_hp,
        max_hp=max_hp,
        temp_hp=0,
        speed_feet=species.speed_feet,
        position=Coordinate(0, 0),
        faction=Faction.ALLY,
        size=CreatureSize(species.size),
        ability_scores=scores,
        spell_slots=tuple(
            SpellSlotState(
                level=level,
                remaining=count,
                maximum=count,
                recovery=character_class.spell_slot_recovery,
            )
            for level, count in _spell_slots_at_level(
                character_class,
                draft.level,
            )
        ),
        spell_save_dc=spell_save_dc,
        inventory=inventory,
        senses=ActorSenseProfile(
            darkvision_feet=max(
                species.darkvision_feet,
                120 if "devils_sight" in class_option_feature_ids else 0,
            ),
            magical_darkness_vision_feet=(
                120 if "devils_sight" in class_option_feature_ids else 0
            ),
        ),
        damage_affinities=DamageAffinityProfile(
            resistances=_species_damage_resistances(species_trait_ids),
        ),
        currency=CurrencyWallet(gp=background.starting_gp),
        spell_ids=tuple(spell.id for spell in spells),
        spell_preparation=spell_preparation,
        spells=spells,
        spell_access=spell_access,
        hit_dice=(
            HitDicePool(
                character_class.hit_die,
                draft.level,
                draft.level,
            ),
        ),
        resource_pools=(
            *_class_resource_pools(
                character_class,
                level=draft.level,
                scores=scores,
                extra_feature_ids=(
                    *class_option_feature_ids,
                    *(
                        _subclass_feature_ids(subclass, draft.level)
                        if subclass is not None
                        else ()
                    ),
                ),
            ),
            *_species_resource_pools(species_trait_ids),
            *_species_innate_spell_resource_pools(
                species,
                draft.level,
            ),
        ),
        level=draft.level,
        proficiency_bonus=2,
        proficiencies=proficiencies,
        uses_death_saves=True,
        features=_feature_grants(
            species=species,
            species_trait_ids=species_trait_ids,
            character_class=character_class,
            background=background,
            subclass=subclass,
            fighting_style_id=draft.selected_fighting_style_id,
            level=draft.level,
            class_option_feature_ids=class_option_feature_ids,
        ),
        portrait=draft.portrait.strip(),
    )
    return CreatedCharacter(
        schema_version=CHARACTER_RECORD_SCHEMA_VERSION,
        actor=actor,
        species_id=species.id,
        class_id=character_class.id,
        background_id=background.id,
        base_ability_scores=draft.base_ability_scores,
        selected_skill_ids=draft.selected_skill_ids,
        selected_expertise_ids=draft.selected_expertise_ids,
        selected_fighting_style_id=draft.selected_fighting_style_id,
        equipment_package_id=package.id,
        item_refs=item_refs,
        selected_cantrip_ids=draft.selected_cantrip_ids,
        selected_spell_ids=draft.selected_spell_ids,
        selected_prepared_spell_ids=draft.selected_prepared_spell_ids,
        selected_subclass_id=draft.selected_subclass_id,
        languages=_unique(
            (
                *species.languages,
                *draft.selected_species_language_ids,
                *background.languages,
                *draft.selected_background_language_ids,
                *(
                    language_id
                    for option in class_options
                    for language_id in option.languages
                ),
            )
        ),
        trait_ids=_unique(
            (
                *species_trait_ids,
                *background.feature_ids,
                *_class_feature_ids(character_class, draft.level),
                *class_option_feature_ids,
            )
            + (
                _subclass_feature_ids(subclass, draft.level)
                if subclass is not None
                else ()
            )
        ),
        selected_species_bonus_ability_ids=draft.selected_species_bonus_ability_ids,
        selected_species_skill_ids=draft.selected_species_skill_ids,
        selected_species_tool_ids=draft.selected_species_tool_ids,
        selected_species_language_ids=draft.selected_species_language_ids,
        selected_species_variant_id=draft.selected_species_variant_id,
        selected_species_cantrip_ids=draft.selected_species_cantrip_ids,
        selected_class_option_ids=draft.selected_class_option_ids,
        selected_background_tool_ids=draft.selected_background_tool_ids,
        selected_background_language_ids=draft.selected_background_language_ids,
    )


def _validate_class_choices(
    draft: CharacterDraft,
    character_class: ClassDefinition,
    species,
    background,
) -> tuple[CharacterValidationIssue, ...]:
    issues: list[CharacterValidationIssue] = []
    selected_options = set(draft.selected_class_option_ids)
    known_options = {
        option.id
        for group in character_class.choice_groups
        for option in group.options
    }
    if len(draft.selected_class_option_ids) != len(selected_options):
        issues.append(
            _issue(
                "selected_class_option_ids",
                "duplicates",
                "Każdą opcję klasową można wybrać tylko raz.",
            )
        )
    if selected_options - known_options:
        issues.append(
            _issue(
                "selected_class_option_ids",
                "unknown",
                "Wybrano nieznaną opcję klasową.",
            )
        )
    for group in character_class.choice_groups:
        group_option_ids = {option.id for option in group.options}
        selected_count = len(selected_options.intersection(group_option_ids))
        requirement_met = (
            not group.requires_option_id
            or group.requires_option_id in selected_options
        )
        expected_count = (
            group.choice_count
            if draft.level >= group.level and requirement_met
            else 0
        )
        if selected_count != expected_count:
            issues.append(
                _issue(
                    "selected_class_option_ids",
                    "wrong_count",
                    f"{group.name}: wybierz dokładnie {expected_count}.",
                )
            )
    if len(draft.selected_skill_ids) != character_class.skill_choice_count:
        issues.append(
            _issue(
                "selected_skill_ids",
                "wrong_count",
                f"Wybierz dokładnie {character_class.skill_choice_count} umiejętności klasowe.",
            )
        )
    unknown_skills = set(draft.selected_skill_ids) - set(character_class.skill_choices)
    if unknown_skills:
        issues.append(_issue("selected_skill_ids", "unknown", "Wybrano umiejętność spoza listy klasy."))
    fixed_skills = {
        *(background.skill_proficiencies if background is not None else ()),
        *(species.skill_proficiencies if species is not None else ()),
        *draft.selected_species_skill_ids,
    }
    if fixed_skills.intersection(draft.selected_skill_ids):
        issues.append(
            _issue(
                "selected_skill_ids",
                "already_granted",
                "Wybierz inną umiejętność: tę biegłość zapewnia już species albo background.",
            )
        )
    final_skills = {
        *(species.skill_proficiencies if species is not None else ()),
        *(background.skill_proficiencies if background is not None else ()),
        *draft.selected_skill_ids,
        *(
            skill_id
            for option in _selected_class_options(
                character_class,
                draft.selected_class_option_ids,
            )
            for skill_id in option.skill_proficiencies
        ),
    }
    expertise_choice_count = (
        character_class.expertise_choice_count
        if draft.level >= character_class.expertise_choice_level
        else 0
    )
    if len(draft.selected_expertise_ids) != expertise_choice_count:
        issues.append(
            _issue(
                "selected_expertise_ids",
                "wrong_count",
                f"Wybierz dokładnie {expertise_choice_count} biegłości Expertise.",
            )
        )
    if set(draft.selected_expertise_ids) - final_skills:
        issues.append(
            _issue(
                "selected_expertise_ids",
                "not_proficient",
                "Expertise można nadać wyłącznie posiadanej biegłości w umiejętności.",
            )
        )
    option_skills = tuple(
        skill_id
        for option in _selected_class_options(
            character_class,
            draft.selected_class_option_ids,
        )
        for skill_id in option.skill_proficiencies
    )
    if len(option_skills) != len(set(option_skills)) or set(
        option_skills
    ).intersection(fixed_skills | set(draft.selected_skill_ids)):
        issues.append(
            _issue(
                "selected_class_option_ids",
                "duplicate_skill",
                "Opcja klasowa musi przyznać nową, dotąd nieposiadaną umiejętność.",
            )
        )
    fighting_style_required = (
        bool(character_class.fighting_style_choices)
        and draft.level >= character_class.fighting_style_choice_level
    )
    if fighting_style_required:
        if draft.selected_fighting_style_id not in character_class.fighting_style_choices:
            issues.append(
                _issue(
                    "selected_fighting_style_id",
                    "unknown",
                    "Wybierz dostępny Fighting Style.",
                )
            )
    elif draft.selected_fighting_style_id:
        issues.append(
            _issue(
                "selected_fighting_style_id",
                "not_available",
                "Ta klasa nie wybiera Fighting Style na poziomie 1.",
            )
        )
    subclass_ids = {item.id for item in character_class.subclass_choices}
    required_subclass_count = (
        character_class.subclass_choice_count
        if draft.level >= character_class.subclass_choice_level
        else 0
    )
    selected_subclass_count = 1 if draft.selected_subclass_id else 0
    if selected_subclass_count != required_subclass_count:
        issues.append(
            _issue(
                "selected_subclass_id",
                "wrong_count",
                f"Wybierz dokładnie {required_subclass_count} archetyp klasy.",
            )
        )
    elif draft.selected_subclass_id not in subclass_ids and draft.selected_subclass_id:
        issues.append(
            _issue(
                "selected_subclass_id",
                "unknown",
                "Wybrano niedostępny archetyp klasy.",
            )
        )
    package_ids = {item.id for item in character_class.equipment_packages}
    if draft.equipment_package_id not in package_ids:
        issues.append(_issue("equipment_package_id", "unknown", "Wybierz dostępny zestaw wyposażenia."))
    cantrip_choice_count = _choice_count_at_level(
        character_class,
        draft.level,
        field="cantrip_choice_count",
        default=character_class.cantrip_choice_count,
    )
    spell_choice_count = _choice_count_at_level(
        character_class,
        draft.level,
        field="spell_choice_count",
        default=character_class.spell_choice_count,
    )
    selected_subclass = next(
        (
            item
            for item in character_class.subclass_choices
            if item.id == draft.selected_subclass_id
        ),
        None,
    )
    selected_class_options = _selected_class_options(
        character_class,
        draft.selected_class_option_ids,
    )
    cantrip_choice_count += sum(
        option.cantrip_choice_count
        for option in selected_class_options
    )
    available_cantrip_choices = _unique(
        (
            *character_class.cantrip_choices,
            *(
                cantrip_id
                for option in selected_class_options
                for cantrip_id in option.cantrip_choices
            ),
        )
    )
    available_spell_choices = _unique(
        (
            *character_class.spell_choices,
            *(
                _progressive_additional_spell_choices(
                    selected_subclass,
                    draft.level,
                )
                if selected_subclass is not None
                else ()
            ),
        )
    )
    for field_name, selected, count, available, label in (
        (
            "selected_cantrip_ids",
            draft.selected_cantrip_ids,
            cantrip_choice_count,
            available_cantrip_choices,
            "cantripy",
        ),
        (
            "selected_spell_ids",
            draft.selected_spell_ids,
            spell_choice_count,
            available_spell_choices,
            "czary",
        ),
    ):
        if len(selected) != count:
            issues.append(_issue(field_name, "wrong_count", f"Wybierz dokładnie {count}: {label}."))
        if set(selected) - set(available):
            issues.append(_issue(field_name, "unknown", f"Wybrano niedostępne {label}."))
    always_prepared = _unique(
        (
            *(
                _progressive_always_prepared_spells(
                    selected_subclass,
                    draft.level,
                )
                if selected_subclass is not None
                else ()
            ),
            *(
                spell_id
                for option in _selected_class_options(
                    character_class,
                    draft.selected_class_option_ids,
                )
                for spell_id in _progressive_always_prepared_spells(
                    option,
                    draft.level,
                )
            ),
        )
    )
    preparation_pool = (
        character_class.spell_choices
        if character_class.preparation_kind == SpellAccessKind.PREPARED.value
        else draft.selected_spell_ids
        if character_class.preparation_kind == SpellAccessKind.SPELLBOOK.value
        else ()
    )
    selectable_preparation = tuple(
        spell_id
        for spell_id in preparation_pool
        if spell_id not in always_prepared
    )
    expected_prepared = _preparation_limit(
        character_class,
        _apply_species_ability_bonuses(
            species,
            draft.base_ability_scores,
            draft.selected_species_bonus_ability_ids,
        )
        if species is not None
        else draft.base_ability_scores,
        selectable_count=len(selectable_preparation),
        level=draft.level,
    )
    if draft.level < character_class.spellcasting_level:
        expected_prepared = 0
    if len(draft.selected_prepared_spell_ids) != expected_prepared:
        issues.append(
            _issue(
                "selected_prepared_spell_ids",
                "wrong_count",
                f"Wybierz dokładnie {expected_prepared} przygotowanych czarów.",
            )
        )
    if set(draft.selected_prepared_spell_ids) - set(selectable_preparation):
        issues.append(
            _issue(
                "selected_prepared_spell_ids",
                "unknown",
                "Przygotowany czar nie znajduje się na dostępnej liście.",
            )
        )
    return tuple(issues)


def _validate_species_choices(
    draft: CharacterDraft,
    species,
) -> tuple[CharacterValidationIssue, ...]:
    issues: list[CharacterValidationIssue] = []
    selections = (
        (
            "selected_species_skill_ids",
            draft.selected_species_skill_ids,
            species.skill_choice_count,
            species.skill_choices,
            "umiejętności species",
        ),
        (
            "selected_species_tool_ids",
            draft.selected_species_tool_ids,
            species.tool_choice_count,
            species.tool_choices,
            "narzędzia species",
        ),
        (
            "selected_species_cantrip_ids",
            draft.selected_species_cantrip_ids,
            species.cantrip_choice_count,
            species.cantrip_choices,
            "cantripy species",
        ),
    )
    for field, selected, count, available, label in selections:
        if len(selected) != len(set(selected)):
            issues.append(_issue(field, "duplicates", f"Powtórzono {label}."))
        if len(selected) != count:
            issues.append(
                _issue(field, "wrong_count", f"Wybierz dokładnie {count}: {label}.")
            )
        if set(selected) - set(available):
            issues.append(_issue(field, "unknown", f"Wybrano niedostępne {label}."))
    selected_languages = draft.selected_species_language_ids
    if len(selected_languages) != len(set(selected_languages)):
        issues.append(
            _issue(
                "selected_species_language_ids",
                "duplicates",
                "Każdy dodatkowy język można wybrać tylko raz.",
            )
        )
    if len(selected_languages) != species.language_choice_count:
        issues.append(
            _issue(
                "selected_species_language_ids",
                "wrong_count",
                f"Wybierz dokładnie {species.language_choice_count} dodatkowych języków.",
            )
        )
    if (
        set(selected_languages) - _LANGUAGE_IDS
        or set(selected_languages).intersection(species.languages)
    ):
        issues.append(
            _issue(
                "selected_species_language_ids",
                "unknown",
                "Wybrano niedostępny albo już posiadany język.",
            )
        )
    selected_variant_count = 1 if draft.selected_species_variant_id else 0
    if selected_variant_count != species.variant_choice_count:
        issues.append(
            _issue(
                "selected_species_variant_id",
                "wrong_count",
                f"Wybierz dokładnie {species.variant_choice_count} wariant species.",
            )
        )
    elif (
        draft.selected_species_variant_id
        and draft.selected_species_variant_id
        not in {item.id for item in species.variant_choices}
    ):
        issues.append(
            _issue(
                "selected_species_variant_id",
                "unknown",
                "Wybrano niedostępny wariant species.",
            )
        )
    return tuple(issues)


def _validate_background_choices(
    draft: CharacterDraft,
    background,
    species,
) -> tuple[CharacterValidationIssue, ...]:
    issues: list[CharacterValidationIssue] = []
    tools = draft.selected_background_tool_ids
    if len(tools) != len(set(tools)):
        issues.append(
            _issue(
                "selected_background_tool_ids",
                "duplicates",
                "Każde narzędzie backgroundu można wybrać tylko raz.",
            )
        )
    if len(tools) != background.tool_choice_count:
        issues.append(
            _issue(
                "selected_background_tool_ids",
                "wrong_count",
                f"Wybierz dokładnie {background.tool_choice_count} narzędzi backgroundu.",
            )
        )
    if set(tools) - set(background.tool_choices):
        issues.append(
            _issue(
                "selected_background_tool_ids",
                "unknown",
                "Wybrano niedostępne narzędzie backgroundu.",
            )
        )
    languages = draft.selected_background_language_ids
    if len(languages) != len(set(languages)):
        issues.append(
            _issue(
                "selected_background_language_ids",
                "duplicates",
                "Każdy język backgroundu można wybrać tylko raz.",
            )
        )
    if len(languages) != background.language_choice_count:
        issues.append(
            _issue(
                "selected_background_language_ids",
                "wrong_count",
                f"Wybierz dokładnie {background.language_choice_count} języków backgroundu.",
            )
        )
    already_known = set(background.languages)
    if species is not None:
        already_known.update(species.languages)
        already_known.update(draft.selected_species_language_ids)
    if set(languages) - _LANGUAGE_IDS or set(languages).intersection(already_known):
        issues.append(
            _issue(
                "selected_background_language_ids",
                "unknown",
                "Wybrano niedostępny albo już posiadany język backgroundu.",
            )
        )
    return tuple(issues)


def _build_inventory(
    grants: tuple[ItemGrant, ...],
    resources: CharacterBuildResources,
) -> tuple[InventoryItem, ...]:
    result: list[InventoryItem] = []
    for grant in grants:
        template = resources.inventory_item(grant.item_id)
        if not isinstance(template, InventoryItem):
            raise ValueError(f"Brakuje definicji przedmiotu: {grant.item_id}.")
        instance_count = grant.quantity if grant.separate_instances else 1
        for index in range(instance_count):
            result.append(
                replace(
                    template,
                    id=(
                        grant.item_id
                        if index == 0
                        else f"{grant.item_id}_{index + 1}"
                    ),
                    quantity=1 if grant.separate_instances else grant.quantity,
                    equipped=grant.equipped,
                    source_ref=grant.item_id,
                    held_in=(),
                )
            )
    return normalize_hand_equipment(result)


def _build_spells(
    spell_ids: tuple[str, ...],
    resources: CharacterBuildResources,
) -> tuple[SpellDefinition, ...]:
    spells: list[SpellDefinition] = []
    for spell_id in spell_ids:
        spell = resources.spell(spell_id)
        if not isinstance(spell, SpellDefinition):
            raise ValueError(f"Brakuje definicji czaru: {spell_id}.")
        spells.append(spell)
    return tuple(spells)


def _spell_profiles(
    character_class: ClassDefinition,
    draft: CharacterDraft,
    spells: tuple[SpellDefinition, ...],
    scores: AbilityScores,
    always_prepared_spell_ids: tuple[str, ...],
    *,
    level: int,
) -> tuple[tuple[SpellAccessProfile, ...], SpellPreparationProfile | None]:
    if (
        character_class.spellcasting_ability is None
        or level < character_class.spellcasting_level
    ):
        return (), None
    kind = SpellAccessKind(character_class.preparation_kind)
    cantrip_ids = tuple(spell.id for spell in spells if spell.level == 0)
    at_will_ids = {
        spell_id
        for option in _selected_class_options(
            character_class,
            draft.selected_class_option_ids,
        )
        for spell_id in option.at_will_spell_ids
    }
    option_ritual_ids = {
        spell_id
        for option in _selected_class_options(
            character_class,
            draft.selected_class_option_ids,
        )
        for spell_id in option.ritual_spell_ids
    }
    leveled_ids = tuple(
        spell.id
        for spell in spells
        if spell.level > 0
        and spell.id not in at_will_ids
        and spell.id not in option_ritual_ids
    )
    focus_kinds = _class_focus_kinds(character_class.id)
    access = tuple(
        profile
        for profile in (
            SpellAccessProfile(
                kind=kind,
                spell_ids=leveled_ids,
                allowed_focus_kinds=focus_kinds,
                casting_ability=character_class.spellcasting_ability,
            )
            if leveled_ids
            else None,
            SpellAccessProfile(
                kind=SpellAccessKind.KNOWN,
                spell_ids=cantrip_ids,
                allowed_focus_kinds=focus_kinds,
                casting_ability=character_class.spellcasting_ability,
            )
            if cantrip_ids
            else None,
        )
        if profile is not None
    )
    if kind not in {SpellAccessKind.PREPARED, SpellAccessKind.SPELLBOOK}:
        return access, None
    maximum_spell_level = max(
        (
            spell_level
            for spell_level, _ in _spell_slots_at_level(character_class, level)
        ),
        default=0,
    )
    leveled = tuple(
        spell
        for spell in spells
        if 0 < spell.level <= maximum_spell_level
    )
    if not leveled:
        return access, None
    prepared_ids = draft.selected_prepared_spell_ids
    selectable_count = len(
        tuple(
            spell
            for spell in leveled
            if spell.id not in always_prepared_spell_ids
        )
    )
    preparation = SpellPreparationProfile(
        source_label=f"lista czarów: {character_class.name}",
        preparation_limit=_preparation_limit(
            character_class,
            scores,
            selectable_count=selectable_count,
            level=level,
        ),
        available_spells=tuple(
            PreparableSpell(id=spell.id, label=spell.name, level=spell.level)
            for spell in leveled
        ),
        prepared_spell_ids=prepared_ids,
        always_prepared_spell_ids=always_prepared_spell_ids,
        confirmed=True,
    )
    return access, preparation


def _species_spell_access(
    species,
    draft: CharacterDraft,
) -> tuple[SpellAccessProfile, ...]:
    cantrip_ids = _unique(
        (
            *draft.selected_species_cantrip_ids,
            *species.fixed_cantrip_ids,
        )
    )
    innate = tuple(
        definition
        for definition in species.innate_spells
        if definition.level <= draft.level
    )
    return tuple(
        profile
        for profile in (
            (
                SpellAccessProfile(
                    kind=SpellAccessKind.KNOWN,
                    spell_ids=cantrip_ids,
                    allowed_focus_kinds=(),
                    casting_ability=species.cantrip_ability,
                )
                if cantrip_ids
                else None
            ),
            (
                SpellAccessProfile(
                    kind=SpellAccessKind.INNATE,
                    spell_ids=tuple(item.spell_id for item in innate),
                    allowed_focus_kinds=(),
                    casting_ability=species.cantrip_ability,
                    resource_ids_by_spell=tuple(
                        (item.spell_id, item.resource_id)
                        for item in innate
                    ),
                )
                if innate
                else None
            ),
        )
        if profile is not None
    )


def _class_option_spell_access(
    character_class: ClassDefinition,
    class_options: tuple[ClassOptionDefinition, ...],
) -> tuple[SpellAccessProfile, ...]:
    spell_ids = _unique(
        tuple(
            spell_id
            for option in class_options
            for spell_id in option.at_will_spell_ids
        )
    )
    ritual_spell_ids = _unique(
        tuple(
            spell_id
            for option in class_options
            for spell_id in option.ritual_spell_ids
        )
    )
    return tuple(
        profile
        for profile in (
            SpellAccessProfile(
            kind=SpellAccessKind.AT_WILL,
            spell_ids=spell_ids,
            allowed_focus_kinds=(
                *_class_focus_kinds(character_class.id),
            ),
            casting_ability=character_class.spellcasting_ability,
            )
            if spell_ids
            else None,
            SpellAccessProfile(
                kind=SpellAccessKind.SPELLBOOK,
                spell_ids=ritual_spell_ids,
                allowed_focus_kinds=_class_focus_kinds(character_class.id),
                casting_ability=character_class.spellcasting_ability,
            )
            if ritual_spell_ids
            else None,
        )
        if profile is not None
    )


def _class_focus_kinds(class_id: str) -> tuple[str, ...]:
    class_focus = {
        "bard": "musical_instrument",
        "cleric": "holy_symbol",
        "druid": "druidic",
        "paladin": "holy_symbol",
        "sorcerer": "arcane",
        "warlock": "arcane",
        "wizard": "arcane",
    }.get(class_id)
    return (
        ("component_pouch", class_focus)
        if class_focus is not None
        else ("component_pouch",)
    )


def _merge_item_grants(grants: tuple[ItemGrant, ...]) -> tuple[ItemGrant, ...]:
    order: list[str] = []
    totals: dict[str, int] = {}
    equipped: dict[str, bool] = {}
    separate: dict[str, bool] = {}
    for grant in grants:
        if grant.item_id not in totals:
            order.append(grant.item_id)
            totals[grant.item_id] = 0
            equipped[grant.item_id] = False
            separate[grant.item_id] = False
        totals[grant.item_id] += grant.quantity
        equipped[grant.item_id] = equipped[grant.item_id] or grant.equipped
        separate[grant.item_id] = (
            separate[grant.item_id] or grant.separate_instances
        )
    return tuple(
        ItemGrant(
            item_id,
            totals[item_id],
            equipped[item_id],
            separate[item_id],
        )
        for item_id in order
    )


def _class_resource_pools(
    character_class: ClassDefinition,
    *,
    level: int,
    scores: AbilityScores,
    extra_feature_ids: tuple[str, ...] = (),
) -> tuple[ActorResourcePool, ...]:
    pools: list[ActorResourcePool] = []
    feature_ids = set(
        (*_class_feature_ids(character_class, level), *extra_feature_ids)
    )
    if "second_wind" in feature_ids:
        pools.append(
            ActorResourcePool(
                id="second_wind_uses",
                label="Second Wind",
                current=1,
                maximum=1,
                recovery=RecoveryPeriod.SHORT_REST,
            )
        )
    if "action_surge" in feature_ids:
        pools.append(
            ActorResourcePool(
                id="action_surge_uses",
                label="Action Surge",
                current=1,
                maximum=1,
                recovery=RecoveryPeriod.SHORT_REST,
            )
        )
    if "channel_divinity" in feature_ids or any(
        feature_id.startswith("channel_divinity_")
        for feature_id in feature_ids
    ):
        pools.append(
            ActorResourcePool(
                id="channel_divinity_uses",
                label="Channel Divinity",
                current=1,
                maximum=1,
                recovery=RecoveryPeriod.SHORT_REST,
            )
        )
    if "arcane_recovery" in feature_ids:
        pools.append(
            ActorResourcePool(
                id="arcane_recovery_uses",
                label="Arcane Recovery",
                current=1,
                maximum=1,
                recovery=RecoveryPeriod.LONG_REST,
            )
        )
    if "natural_recovery" in feature_ids:
        pools.append(
            ActorResourcePool(
                id="natural_recovery_uses",
                label="Natural Recovery",
                current=1,
                maximum=1,
                recovery=RecoveryPeriod.LONG_REST,
            )
        )
    resource_specs = (
        (
            "rage",
            "rage_uses",
            "Rage",
            3 if level >= 3 else 2,
            RecoveryPeriod.LONG_REST,
        ),
        (
            "bardic_inspiration",
            "bardic_inspiration_uses",
            "Bardic Inspiration",
            max(1, ability_modifier(scores.charisma)),
            RecoveryPeriod.LONG_REST,
        ),
        (
            "divine_sense",
            "divine_sense_uses",
            "Divine Sense",
            max(1, 1 + ability_modifier(scores.charisma)),
            RecoveryPeriod.LONG_REST,
        ),
        (
            "lay_on_hands",
            "lay_on_hands_points",
            "Lay on Hands",
            level * 5,
            RecoveryPeriod.LONG_REST,
        ),
        ("wild_shape", "wild_shape_uses", "Wild Shape", 2, RecoveryPeriod.SHORT_REST),
        ("ki", "ki_points", "Ki", level, RecoveryPeriod.SHORT_REST),
        (
            "font_of_magic",
            "sorcery_points",
            "Sorcery Points",
            level,
            RecoveryPeriod.LONG_REST,
        ),
    )
    for feature_id, resource_id, label, maximum, recovery in resource_specs:
        if feature_id in feature_ids:
            pools.append(
                ActorResourcePool(
                    id=resource_id,
                    label=label,
                    current=maximum,
                    maximum=maximum,
                    recovery=recovery,
                )
            )
    return tuple(pools)


def _species_resource_pools(
    trait_ids: tuple[str, ...],
) -> tuple[ActorResourcePool, ...]:
    pools: list[ActorResourcePool] = []
    if "breath_weapon" in trait_ids:
        pools.append(
            ActorResourcePool(
                id="breath_weapon_uses",
                label="Breath Weapon",
                current=1,
                maximum=1,
                recovery=RecoveryPeriod.SHORT_REST,
            )
        )
    if "relentless_endurance" in trait_ids:
        pools.append(
            ActorResourcePool(
                id="relentless_endurance_uses",
                label="Relentless Endurance",
                current=1,
                maximum=1,
                recovery=RecoveryPeriod.LONG_REST,
            )
        )
    return tuple(pools)


def _species_innate_spell_resource_pools(
    species,
    level: int,
) -> tuple[ActorResourcePool, ...]:
    return tuple(
        ActorResourcePool(
            id=definition.resource_id,
            label=f"Innate Spell: {definition.spell_id.replace('_', ' ').title()}",
            current=1,
            maximum=1,
            recovery=RecoveryPeriod(definition.recovery),
        )
        for definition in species.innate_spells
        if definition.level <= level
    )


def _feature_grants(
    *,
    species,
    species_trait_ids: tuple[str, ...],
    character_class: ClassDefinition,
    background,
    subclass,
    fighting_style_id: str,
    level: int,
    class_option_feature_ids: tuple[str, ...] = (),
) -> tuple[FeatureGrant, ...]:
    grants: list[FeatureGrant] = []
    for feature_id in species_trait_ids:
        breath_weapon = feature_id == "breath_weapon"
        relentless_endurance = feature_id == "relentless_endurance"
        grants.append(
            FeatureGrant(
                feature_id=feature_id,
                label=_feature_label(feature_id),
                source_kind=FeatureSourceKind.SPECIES,
                source_ref=species.id,
                resource_ids=(
                    ("breath_weapon_uses",)
                    if breath_weapon
                    else ("relentless_endurance_uses",)
                    if relentless_endurance
                    else ()
                ),
                action_ids=("breath_weapon",) if breath_weapon else (),
            )
        )
    for feature_id in background.feature_ids:
        grants.append(
            FeatureGrant(
                feature_id=feature_id,
                label=_feature_label(feature_id),
                source_kind=FeatureSourceKind.BACKGROUND,
                source_ref=background.id,
                action_ids=background.permission_ids,
            )
        )
    for feature_id in _class_feature_ids(character_class, level):
        if feature_id == "fighting_style":
            continue
        resource_ids = _feature_resource_ids(feature_id)
        action_ids = _feature_action_ids(feature_id)
        grants.append(
            FeatureGrant(
                feature_id=feature_id,
                label=_feature_label(feature_id),
                source_kind=FeatureSourceKind.CLASS,
                source_ref=character_class.id,
                resource_ids=resource_ids,
                action_ids=action_ids,
            )
        )
    if subclass is not None:
        for feature_id in _subclass_feature_ids(subclass, level):
            grants.append(
                FeatureGrant(
                    feature_id=feature_id,
                    label=_feature_label(feature_id),
                    source_kind=FeatureSourceKind.SUBCLASS,
                    source_ref=subclass.id,
                    resource_ids=_feature_resource_ids(feature_id),
                    action_ids=_feature_action_ids(feature_id),
                )
            )
    if fighting_style_id:
        feature_id = f"fighting_style_{fighting_style_id}"
        grants.append(
            FeatureGrant(
                feature_id=feature_id,
                label=_feature_label(feature_id),
                source_kind=FeatureSourceKind.CLASS,
                source_ref=character_class.id,
            )
        )
    for feature_id in class_option_feature_ids:
        grants.append(
            FeatureGrant(
                feature_id=feature_id,
                label=_feature_label(feature_id),
                source_kind=FeatureSourceKind.CLASS,
                source_ref=character_class.id,
                resource_ids=_feature_resource_ids(feature_id),
                action_ids=_feature_action_ids(feature_id),
            )
        )
    return tuple(grants)


def _feature_resource_ids(feature_id: str) -> tuple[str, ...]:
    if feature_id.startswith("channel_divinity_") or feature_id in {
        "channel_divinity",
        "turn_undead",
    }:
        return ("channel_divinity_uses",)
    return {
        "second_wind": ("second_wind_uses",),
        "action_surge": ("action_surge_uses",),
        "arcane_recovery": ("arcane_recovery_uses",),
        "natural_recovery": ("natural_recovery_uses",),
        "rage": ("rage_uses",),
        "bardic_inspiration": ("bardic_inspiration_uses",),
        "divine_sense": ("divine_sense_uses",),
        "lay_on_hands": ("lay_on_hands_points",),
        "wild_shape": ("wild_shape_uses",),
        "ki": ("ki_points",),
        "font_of_magic": ("sorcery_points",),
    }.get(feature_id, ())


def _feature_action_ids(feature_id: str) -> tuple[str, ...]:
    return {
        "second_wind": ("second_wind",),
        "action_surge": ("action_surge",),
        "cunning_action": ("cunning_action",),
        "turn_undead": ("turn_undead",),
        "channel_divinity_preserve_life": ("preserve_life",),
        "channel_divinity_sacred_weapon": ("sacred_weapon",),
        "channel_divinity_turn_the_unholy": ("turn_the_unholy",),
        "arcane_recovery": ("arcane_recovery",),
        "sneak_attack": ("sneak_attack",),
        "rage": ("rage",),
        "reckless_attack": ("reckless_attack",),
        "bardic_inspiration": ("bardic_inspiration",),
        "cutting_words": ("cutting_words",),
        "divine_sense": ("divine_sense",),
        "lay_on_hands": ("lay_on_hands",),
        "divine_smite": ("divine_smite",),
        "wild_shape": ("wild_shape",),
        "martial_arts": ("martial_arts_bonus_attack",),
        "ki": ("flurry_of_blows", "patient_defense", "step_of_the_wind"),
        "deflect_missiles": ("deflect_missiles",),
        "font_of_magic": ("font_of_magic",),
        "frenzy": ("frenzy",),
        "primeval_awareness": ("primeval_awareness",),
        "pact_of_the_blade": ("pact_weapon",),
    }.get(feature_id, ())


def _feature_label(feature_id: str) -> str:
    return player_label(feature_id)


def _unarmored_armor_class(
    scores: AbilityScores,
    class_feature_ids: tuple[str, ...],
    subclass_feature_ids: tuple[str, ...],
) -> int:
    feature_ids = set((*class_feature_ids, *subclass_feature_ids))
    dexterity = ability_modifier(scores.dexterity)
    candidates = [10 + dexterity]
    if "unarmored_defense_constitution" in feature_ids:
        candidates.append(10 + dexterity + ability_modifier(scores.constitution))
    if "unarmored_defense_wisdom" in feature_ids:
        candidates.append(10 + dexterity + ability_modifier(scores.wisdom))
    if "draconic_resilience" in feature_ids:
        candidates.append(13 + dexterity)
    return max(candidates)


def _ability_values(scores: AbilityScores) -> tuple[int, ...]:
    return tuple(getattr(scores, ability) for ability in ABILITY_IDS)


def _apply_species_ability_bonuses(
    species,
    scores: AbilityScores,
    selected_bonus_abilities: tuple[str, ...],
) -> AbilityScores:
    fixed = species.ability_bonuses.apply(scores)
    return replace(
        fixed,
        **{
            ability: getattr(fixed, ability) + species.ability_bonus_choice_value
            for ability in selected_bonus_abilities
        },
    )


def _species_damage_resistances(
    trait_ids: tuple[str, ...],
) -> tuple[DamageType, ...]:
    mapping = {
        "dwarven_resilience": DamageType.POISON,
        "damage_resistance_acid": DamageType.ACID,
        "damage_resistance_cold": DamageType.COLD,
        "damage_resistance_fire": DamageType.FIRE,
        "damage_resistance_lightning": DamageType.LIGHTNING,
        "damage_resistance_poison": DamageType.POISON,
        "hellish_resistance": DamageType.FIRE,
    }
    return tuple(
        dict.fromkeys(
            mapping[feature_id]
            for feature_id in trait_ids
            if feature_id in mapping
        )
    )


def _preparation_limit(
    character_class: ClassDefinition,
    scores: AbilityScores,
    *,
    selectable_count: int,
    level: int,
) -> int:
    if not character_class.preparation_formula:
        return 0
    if character_class.spellcasting_ability is None:
        raise ValueError("Preparation formula requires a spellcasting ability.")
    class_level = (
        level // 2
        if character_class.preparation_formula == "ability_modifier_plus_half_level"
        else level
    )
    limit = max(
        1,
        ability_modifier(getattr(scores, character_class.spellcasting_ability))
        + class_level,
    )
    return min(limit, selectable_count)


def _class_feature_ids(
    character_class: ClassDefinition,
    level: int,
) -> tuple[str, ...]:
    return _unique(
        (
            *character_class.feature_ids,
            *(
                feature_id
                for entry in character_class.level_progression
                if entry.level <= level
                for feature_id in entry.feature_ids
            ),
        )
    )


def _selected_class_options(
    character_class: ClassDefinition,
    selected_option_ids: tuple[str, ...],
) -> tuple[ClassOptionDefinition, ...]:
    selected = set(selected_option_ids)
    return tuple(
        option
        for group in character_class.choice_groups
        for option in group.options
        if option.id in selected
    )


def _progressive_always_prepared_spells(
    source,
    level: int,
) -> tuple[str, ...]:
    return _unique(
        (
            *source.always_prepared_spell_ids,
            *(
                spell_id
                for entry in source.level_progression
                if entry.level <= level
                for spell_id in entry.always_prepared_spell_ids
            ),
        )
    )


def _progressive_additional_spell_choices(
    source,
    level: int,
) -> tuple[str, ...]:
    return _unique(
        (
            *source.additional_spell_choice_ids,
            *(
                spell_id
                for entry in source.level_progression
                if entry.level <= level
                for spell_id in entry.additional_spell_choice_ids
            ),
        )
    )


def _subclass_feature_ids(
    subclass,
    level: int,
) -> tuple[str, ...]:
    return _unique(
        (
            *subclass.feature_ids,
            *(
                feature_id
                for entry in subclass.level_progression
                if entry.level <= level
                for feature_id in entry.feature_ids
            ),
        )
    )


def _spell_slots_at_level(
    character_class: ClassDefinition,
    level: int,
) -> tuple[tuple[int, int], ...]:
    selected = character_class.spell_slots
    for entry in character_class.level_progression:
        if entry.level <= level and entry.spell_slots:
            selected = entry.spell_slots
    return selected


def _choice_count_at_level(
    character_class: ClassDefinition,
    level: int,
    *,
    field: str,
    default: int,
) -> int:
    selected = default
    for entry in character_class.level_progression:
        if entry.level > level:
            break
        value = getattr(entry, field)
        if value is not None:
            selected = value
    return selected


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _issue(field: str, code: str, message: str) -> CharacterValidationIssue:
    return CharacterValidationIssue(field, code, message)
