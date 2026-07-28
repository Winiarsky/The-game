"""Transport-neutral character-creation definitions and draft state."""

from __future__ import annotations

from dataclasses import dataclass, field

from dnd_board_game.actors import AbilityScores, Actor
from dnd_board_game.inventory import InventoryItem
from dnd_board_game.rules import SpellDefinition


CHARACTER_RECORD_SCHEMA_VERSION = 7
STANDARD_ARRAY = (15, 14, 13, 12, 10, 8)
ABILITY_IDS = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)


@dataclass(frozen=True, slots=True)
class AbilityScoreBonuses:
    strength: int = 0
    dexterity: int = 0
    constitution: int = 0
    intelligence: int = 0
    wisdom: int = 0
    charisma: int = 0

    def apply(self, scores: AbilityScores) -> AbilityScores:
        return AbilityScores(
            strength=scores.strength + self.strength,
            dexterity=scores.dexterity + self.dexterity,
            constitution=scores.constitution + self.constitution,
            intelligence=scores.intelligence + self.intelligence,
            wisdom=scores.wisdom + self.wisdom,
            charisma=scores.charisma + self.charisma,
        )


@dataclass(frozen=True, slots=True)
class ItemGrant:
    item_id: str
    quantity: int = 1
    equipped: bool = True
    separate_instances: bool = False

    def __post_init__(self) -> None:
        if not self.item_id.strip():
            raise ValueError("Item grant requires a non-empty item id.")
        if self.quantity < 1:
            raise ValueError("Item grant quantity must be positive.")


@dataclass(frozen=True, slots=True)
class EquipmentPackage:
    id: str
    label: str
    items: tuple[ItemGrant, ...]

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.label.strip():
            raise ValueError("Equipment package requires an id and label.")
        if not self.items:
            raise ValueError("Equipment package cannot be empty.")


@dataclass(frozen=True, slots=True)
class CharacterLevelDefinition:
    level: int
    feature_ids: tuple[str, ...] = ()
    spell_slots: tuple[tuple[int, int], ...] = ()
    cantrip_choice_count: int | None = None
    spell_choice_count: int | None = None
    always_prepared_spell_ids: tuple[str, ...] = ()
    additional_spell_choice_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not 1 <= self.level <= 20:
            raise ValueError("Character progression level must be between 1 and 20.")
        if self.cantrip_choice_count is not None and self.cantrip_choice_count < 0:
            raise ValueError("Cantrip choice count cannot be negative.")
        if self.spell_choice_count is not None and self.spell_choice_count < 0:
            raise ValueError("Spell choice count cannot be negative.")


@dataclass(frozen=True, slots=True)
class ClassOptionDefinition:
    id: str
    name: str
    feature_ids: tuple[str, ...] = ()
    tool_proficiencies: tuple[str, ...] = ()
    skill_proficiencies: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    always_prepared_spell_ids: tuple[str, ...] = ()
    at_will_spell_ids: tuple[str, ...] = ()
    ritual_spell_ids: tuple[str, ...] = ()
    cantrip_choice_count: int = 0
    cantrip_choices: tuple[str, ...] = ()
    level_progression: tuple[CharacterLevelDefinition, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Class option requires an id and name.")
        if not 0 <= self.cantrip_choice_count <= len(self.cantrip_choices):
            raise ValueError("Class option cantrip choice count is invalid.")
        _validate_level_progression(self.level_progression, "Class option")


@dataclass(frozen=True, slots=True)
class ClassChoiceGroupDefinition:
    id: str
    name: str
    level: int
    choice_count: int
    options: tuple[ClassOptionDefinition, ...]
    requires_option_id: str = ""

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Class choice group requires an id and name.")
        if not 1 <= self.level <= 20:
            raise ValueError("Class choice group level must be between 1 and 20.")
        if self.choice_count < 1 or self.choice_count > len(self.options):
            raise ValueError("Class choice group count exceeds its options.")
        ids = tuple(option.id for option in self.options)
        if len(ids) != len(set(ids)):
            raise ValueError("Class choice group option ids must be unique.")


@dataclass(frozen=True, slots=True)
class SubclassDefinition:
    id: str
    name: str
    feature_ids: tuple[str, ...] = ()
    armor_proficiencies: tuple[str, ...] = ()
    weapon_proficiencies: tuple[str, ...] = ()
    always_prepared_spell_ids: tuple[str, ...] = ()
    additional_spell_choice_ids: tuple[str, ...] = ()
    level_progression: tuple[CharacterLevelDefinition, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Subclass requires an id and name.")
        _validate_level_progression(self.level_progression, "Subclass")


@dataclass(frozen=True, slots=True)
class SpeciesVariantDefinition:
    id: str
    name: str
    trait_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Species variant requires an id and name.")


@dataclass(frozen=True, slots=True)
class SpeciesInnateSpellDefinition:
    spell_id: str
    level: int
    resource_id: str
    recovery: str = "long_rest"

    def __post_init__(self) -> None:
        if not self.spell_id.strip() or not self.resource_id.strip():
            raise ValueError("Innate spell requires spell and resource ids.")
        if not 1 <= self.level <= 20:
            raise ValueError("Innate spell grant level must be between 1 and 20.")
        if self.recovery not in {"short_rest", "long_rest"}:
            raise ValueError("Innate spell recovery is unknown.")


@dataclass(frozen=True, slots=True)
class SpeciesDefinition:
    id: str
    name: str
    speed_feet: int
    description: str = ""
    size: str = "medium"
    ability_bonuses: AbilityScoreBonuses = field(default_factory=AbilityScoreBonuses)
    darkvision_feet: int = 0
    skill_proficiencies: tuple[str, ...] = ()
    weapon_proficiencies: tuple[str, ...] = ()
    tool_proficiencies: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    trait_ids: tuple[str, ...] = ()
    ability_bonus_choice_count: int = 0
    ability_bonus_choice_value: int = 1
    ability_bonus_choice_exclusions: tuple[str, ...] = ()
    skill_choice_count: int = 0
    skill_choices: tuple[str, ...] = ()
    tool_choice_count: int = 0
    tool_choices: tuple[str, ...] = ()
    language_choice_count: int = 0
    variant_choice_count: int = 0
    variant_choices: tuple[SpeciesVariantDefinition, ...] = ()
    cantrip_choice_count: int = 0
    cantrip_choices: tuple[str, ...] = ()
    fixed_cantrip_ids: tuple[str, ...] = ()
    innate_spells: tuple[SpeciesInnateSpellDefinition, ...] = ()
    cantrip_ability: str | None = None

    def __post_init__(self) -> None:
        if self.size not in {"tiny", "small", "medium", "large", "huge", "gargantuan"}:
            raise ValueError("Species size is unknown.")
        if not 0 <= self.ability_bonus_choice_count <= len(ABILITY_IDS):
            raise ValueError("Species ability bonus choice count is invalid.")
        if self.ability_bonus_choice_value < 1:
            raise ValueError("Species ability bonus choice value must be positive.")
        if set(self.ability_bonus_choice_exclusions) - set(ABILITY_IDS):
            raise ValueError("Species ability bonus choice exclusion is unknown.")
        for count, choices, label in (
            (self.skill_choice_count, self.skill_choices, "skill"),
            (self.tool_choice_count, self.tool_choices, "tool"),
            (self.variant_choice_count, self.variant_choices, "variant"),
            (self.cantrip_choice_count, self.cantrip_choices, "cantrip"),
        ):
            if count < 0 or count > len(choices):
                raise ValueError(f"Species {label} choice count is invalid.")
        if self.language_choice_count < 0:
            raise ValueError("Species language choice count cannot be negative.")
        if self.cantrip_ability is not None and self.cantrip_ability not in ABILITY_IDS:
            raise ValueError("Species cantrip ability is unknown.")
        if (self.cantrip_choice_count or self.fixed_cantrip_ids) and self.cantrip_ability is None:
            raise ValueError("Species cantrip choices require a casting ability.")


@dataclass(frozen=True, slots=True)
class ClassDefinition:
    id: str
    name: str
    hit_die: int
    saving_throw_proficiencies: tuple[str, ...]
    skill_choice_count: int
    skill_choices: tuple[str, ...]
    description: str = ""
    weapon_proficiencies: tuple[str, ...] = ()
    armor_proficiencies: tuple[str, ...] = ()
    tool_proficiencies: tuple[str, ...] = ()
    equipment_packages: tuple[EquipmentPackage, ...] = ()
    feature_ids: tuple[str, ...] = ()
    fighting_style_choices: tuple[str, ...] = ()
    fighting_style_choice_level: int = 1
    expertise_choice_count: int = 0
    expertise_choice_level: int = 1
    spellcasting_ability: str | None = None
    spellcasting_level: int = 1
    cantrip_choice_count: int = 0
    cantrip_choices: tuple[str, ...] = ()
    spell_choice_count: int = 0
    spell_choices: tuple[str, ...] = ()
    spell_slots: tuple[tuple[int, int], ...] = ()
    spell_slot_recovery: str = "long_rest"
    preparation_kind: str = ""
    preparation_formula: str = ""
    subclass_choice_count: int = 0
    subclass_choice_level: int = 1
    subclass_choices: tuple[SubclassDefinition, ...] = ()
    level_progression: tuple[CharacterLevelDefinition, ...] = ()
    choice_groups: tuple[ClassChoiceGroupDefinition, ...] = ()

    def __post_init__(self) -> None:
        if self.hit_die not in {6, 8, 10, 12}:
            raise ValueError("Class hit die must be d6, d8, d10, or d12.")
        if self.skill_choice_count < 0 or self.skill_choice_count > len(self.skill_choices):
            raise ValueError("Class skill choice count exceeds its choice pool.")
        if self.cantrip_choice_count < 0 or self.cantrip_choice_count > len(self.cantrip_choices):
            raise ValueError("Class cantrip choice count exceeds its choice pool.")
        if self.spell_choice_count < 0 or self.spell_choice_count > len(self.spell_choices):
            raise ValueError("Class spell choice count exceeds its choice pool.")
        if self.expertise_choice_count < 0:
            raise ValueError("Class expertise choice count cannot be negative.")
        if not 1 <= self.fighting_style_choice_level <= 20:
            raise ValueError("Fighting Style choice level must be between 1 and 20.")
        if not 1 <= self.expertise_choice_level <= 20:
            raise ValueError("Expertise choice level must be between 1 and 20.")
        if not 1 <= self.spellcasting_level <= 20:
            raise ValueError("Spellcasting level must be between 1 and 20.")
        if self.spellcasting_ability is not None and self.spellcasting_ability not in ABILITY_IDS:
            raise ValueError("Class spellcasting ability is unknown.")
        if self.preparation_kind not in {"", "prepared", "spellbook", "known"}:
            raise ValueError("Unknown spell preparation kind.")
        if self.preparation_formula not in {
            "",
            "ability_modifier_plus_level",
            "ability_modifier_plus_half_level",
        }:
            raise ValueError("Unknown spell preparation formula.")
        if self.spell_slot_recovery not in {"short_rest", "long_rest"}:
            raise ValueError("Unknown spell slot recovery period.")
        if self.subclass_choice_count < 0 or self.subclass_choice_count > len(self.subclass_choices):
            raise ValueError("Class subclass choice count exceeds its choice pool.")
        if not 1 <= self.subclass_choice_level <= 20:
            raise ValueError("Class subclass choice level must be between 1 and 20.")
        _validate_level_progression(self.level_progression, "Class")
        group_ids = tuple(group.id for group in self.choice_groups)
        if len(group_ids) != len(set(group_ids)):
            raise ValueError("Class choice group ids must be unique.")
        option_ids = {
            option.id
            for group in self.choice_groups
            for option in group.options
        }
        for group in self.choice_groups:
            if group.requires_option_id and group.requires_option_id not in option_ids:
                raise ValueError(
                    f"Class choice group {group.id} requires an unknown option."
                )
            if group.requires_option_id in {
                option.id for option in group.options
            }:
                raise ValueError(
                    f"Class choice group {group.id} cannot require itself."
                )
        subclass_ids = tuple(item.id for item in self.subclass_choices)
        if len(subclass_ids) != len(set(subclass_ids)):
            raise ValueError("Class subclass choices must be unique.")
        if self.preparation_formula and self.preparation_kind not in {"prepared", "spellbook"}:
            raise ValueError("Preparation formula requires prepared or spellbook casting.")


@dataclass(frozen=True, slots=True)
class BackgroundDefinition:
    id: str
    name: str
    description: str = ""
    skill_proficiencies: tuple[str, ...] = ()
    tool_proficiencies: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    tool_choice_count: int = 0
    tool_choices: tuple[str, ...] = ()
    language_choice_count: int = 0
    equipment: tuple[ItemGrant, ...] = ()
    starting_gp: int = 0
    feature_ids: tuple[str, ...] = ()
    permission_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.tool_choice_count < 0 or self.tool_choice_count > len(self.tool_choices):
            raise ValueError("Background tool choice count exceeds its choice pool.")
        if self.language_choice_count < 0:
            raise ValueError("Background language choice count cannot be negative.")


@dataclass(frozen=True, slots=True)
class CharacterCatalog:
    schema_version: int
    species: tuple[SpeciesDefinition, ...]
    classes: tuple[ClassDefinition, ...]
    backgrounds: tuple[BackgroundDefinition, ...]

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ValueError("Character catalog schema_version must be 1.")
        for label, definitions in (
            ("species", self.species),
            ("class", self.classes),
            ("background", self.backgrounds),
        ):
            ids = tuple(definition.id for definition in definitions)
            if not definitions:
                raise ValueError(f"Character catalog requires at least one {label}.")
            if len(ids) != len(set(ids)):
                raise ValueError(f"Character catalog contains duplicate {label} ids.")

    def species_by_id(self, definition_id: str) -> SpeciesDefinition | None:
        return next((item for item in self.species if item.id == definition_id), None)

    def class_by_id(self, definition_id: str) -> ClassDefinition | None:
        return next((item for item in self.classes if item.id == definition_id), None)

    def background_by_id(self, definition_id: str) -> BackgroundDefinition | None:
        return next((item for item in self.backgrounds if item.id == definition_id), None)


@dataclass(frozen=True, slots=True)
class CharacterDraft:
    id: str
    name: str
    species_id: str
    class_id: str
    background_id: str
    base_ability_scores: AbilityScores
    selected_skill_ids: tuple[str, ...] = ()
    selected_expertise_ids: tuple[str, ...] = ()
    selected_fighting_style_id: str = ""
    equipment_package_id: str = ""
    selected_cantrip_ids: tuple[str, ...] = ()
    selected_spell_ids: tuple[str, ...] = ()
    selected_prepared_spell_ids: tuple[str, ...] = ()
    selected_subclass_id: str = ""
    portrait: str = ""
    level: int = 1
    selected_species_bonus_ability_ids: tuple[str, ...] = ()
    selected_species_skill_ids: tuple[str, ...] = ()
    selected_species_tool_ids: tuple[str, ...] = ()
    selected_species_language_ids: tuple[str, ...] = ()
    selected_species_variant_id: str = ""
    selected_species_cantrip_ids: tuple[str, ...] = ()
    selected_class_option_ids: tuple[str, ...] = ()
    selected_background_tool_ids: tuple[str, ...] = ()
    selected_background_language_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CharacterValidationIssue:
    field: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class CharacterValidation:
    issues: tuple[CharacterValidationIssue, ...] = ()

    @property
    def valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True, slots=True)
class CharacterBuildResources:
    inventory_items: tuple[tuple[str, InventoryItem], ...] = ()
    spells: tuple[tuple[str, SpellDefinition], ...] = ()

    def inventory_item(self, item_id: str) -> InventoryItem | None:
        return next((item for key, item in self.inventory_items if key == item_id), None)

    def spell(self, spell_id: str) -> SpellDefinition | None:
        return next((spell for key, spell in self.spells if key == spell_id), None)


@dataclass(frozen=True, slots=True)
class CreatedCharacter:
    schema_version: int
    actor: Actor
    species_id: str
    class_id: str
    background_id: str
    base_ability_scores: AbilityScores
    selected_skill_ids: tuple[str, ...]
    selected_expertise_ids: tuple[str, ...]
    selected_fighting_style_id: str
    equipment_package_id: str
    item_refs: tuple[ItemGrant, ...]
    selected_cantrip_ids: tuple[str, ...]
    selected_spell_ids: tuple[str, ...]
    selected_prepared_spell_ids: tuple[str, ...]
    selected_subclass_id: str
    languages: tuple[str, ...]
    trait_ids: tuple[str, ...]
    selected_species_bonus_ability_ids: tuple[str, ...] = ()
    selected_species_skill_ids: tuple[str, ...] = ()
    selected_species_tool_ids: tuple[str, ...] = ()
    selected_species_language_ids: tuple[str, ...] = ()
    selected_species_variant_id: str = ""
    selected_species_cantrip_ids: tuple[str, ...] = ()
    selected_class_option_ids: tuple[str, ...] = ()
    selected_background_tool_ids: tuple[str, ...] = ()
    selected_background_language_ids: tuple[str, ...] = ()


def _validate_level_progression(
    progression: tuple[CharacterLevelDefinition, ...],
    label: str,
) -> None:
    levels = tuple(entry.level for entry in progression)
    if len(levels) != len(set(levels)):
        raise ValueError(f"{label} level progression contains duplicate levels.")
    if levels != tuple(sorted(levels)):
        raise ValueError(f"{label} level progression must be ordered.")
