"""Authoritative SRD 5.1 character-content target for levels 1-3.

The manifest intentionally uses canonical snake-case ids.  Scenario-only spell
variants do not satisfy this contract: a complete character catalog must expose
the actual SRD spell under its canonical id.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

from .models import CharacterCatalog


SRD_SPECIES_IDS = (
    "human",
    "elf",
    "dwarf",
    "halfling",
    "dragonborn",
    "gnome",
    "half_elf",
    "half_orc",
    "tiefling",
)

SRD_CLASS_SUBCLASS_IDS = {
    "barbarian": "path_of_the_berserker",
    "bard": "college_of_lore",
    "cleric": "life_domain",
    "druid": "circle_of_the_land",
    "fighter": "champion",
    "monk": "way_of_the_open_hand",
    "paladin": "oath_of_devotion",
    "ranger": "hunter",
    "rogue": "thief",
    "sorcerer": "draconic_bloodline",
    "warlock": "the_fiend",
    "wizard": "school_of_evocation",
}

SRD_SPELL_IDS_BY_LEVEL = {
    0: (
        "acid_splash", "chill_touch", "dancing_lights", "druidcraft",
        "eldritch_blast", "fire_bolt", "guidance", "light", "mage_hand",
        "mending", "message", "minor_illusion", "poison_spray",
        "prestidigitation", "produce_flame", "ray_of_frost", "resistance", "sacred_flame",
        "shillelagh", "shocking_grasp", "spare_the_dying", "thaumaturgy",
        "true_strike", "vicious_mockery",
    ),
    1: (
        "alarm", "animal_friendship", "bane", "bless", "burning_hands",
        "charm_person", "color_spray", "command", "comprehend_languages",
        "create_or_destroy_water", "cure_wounds", "detect_evil_and_good",
        "detect_magic", "detect_poison_and_disease", "disguise_self",
        "divine_favor", "entangle", "expeditious_retreat", "faerie_fire",
        "false_life", "feather_fall", "find_familiar", "floating_disk",
        "fog_cloud", "goodberry", "grease", "guiding_bolt", "healing_word",
        "hellish_rebuke", "heroism", "hideous_laughter", "hunters_mark",
        "identify", "illusory_script", "inflict_wounds", "jump",
        "longstrider", "mage_armor", "magic_missile",
        "protection_from_evil_and_good", "purify_food_and_drink",
        "sanctuary", "shield", "shield_of_faith", "silent_image", "sleep",
        "speak_with_animals", "thunderwave", "unseen_servant",
    ),
    2: (
        "acid_arrow", "aid", "alter_self", "animal_messenger",
        "arcane_lock", "arcanists_magic_aura", "augury", "barkskin",
        "blindness_deafness", "blur", "branding_smite", "calm_emotions",
        "continual_flame", "darkness", "darkvision", "detect_thoughts",
        "enhance_ability", "enlarge_reduce", "enthrall", "find_steed",
        "find_traps", "flame_blade", "flaming_sphere", "gentle_repose",
        "gust_of_wind", "heat_metal", "hold_person", "invisibility", "knock",
        "lesser_restoration", "levitate", "locate_animals_or_plants",
        "locate_object", "magic_mouth", "magic_weapon", "mirror_image",
        "misty_step", "moonbeam", "pass_without_trace", "prayer_of_healing",
        "protection_from_poison", "ray_of_enfeeblement", "rope_trick",
        "scorching_ray", "see_invisibility", "shatter", "silence",
        "spider_climb", "spike_growth", "spiritual_weapon", "suggestion",
        "warding_bond", "web", "zone_of_truth",
    ),
}

SRD_CLASS_SPELL_IDS = {
    "bard": (
        "dancing_lights", "light", "mage_hand", "mending", "message",
        "minor_illusion", "prestidigitation", "true_strike", "vicious_mockery",
        "animal_friendship", "bane", "charm_person", "comprehend_languages",
        "cure_wounds", "detect_magic", "disguise_self", "faerie_fire",
        "feather_fall", "healing_word", "heroism", "hideous_laughter",
        "identify", "illusory_script", "longstrider", "silent_image", "sleep",
        "speak_with_animals", "thunderwave", "unseen_servant",
        "animal_messenger", "blindness_deafness", "calm_emotions",
        "detect_thoughts", "enhance_ability", "enthrall", "heat_metal",
        "hold_person", "invisibility", "knock", "lesser_restoration",
        "locate_animals_or_plants", "locate_object", "magic_mouth",
        "see_invisibility", "shatter", "silence", "suggestion", "zone_of_truth",
    ),
    "cleric": (
        "guidance", "light", "mending", "resistance", "sacred_flame",
        "spare_the_dying", "thaumaturgy", "bane", "bless", "command",
        "create_or_destroy_water", "cure_wounds", "detect_evil_and_good",
        "detect_magic", "detect_poison_and_disease", "guiding_bolt",
        "healing_word", "inflict_wounds", "protection_from_evil_and_good",
        "purify_food_and_drink", "sanctuary", "shield_of_faith", "aid", "augury",
        "blindness_deafness", "calm_emotions", "continual_flame",
        "enhance_ability", "find_traps", "gentle_repose", "hold_person",
        "lesser_restoration", "locate_object", "prayer_of_healing",
        "protection_from_poison", "silence", "spiritual_weapon", "warding_bond",
        "zone_of_truth",
    ),
    "druid": (
        "druidcraft", "guidance", "mending", "poison_spray", "produce_flame",
        "resistance", "shillelagh", "animal_friendship", "charm_person",
        "create_or_destroy_water", "cure_wounds", "detect_magic",
        "detect_poison_and_disease", "entangle", "faerie_fire", "fog_cloud",
        "goodberry", "healing_word", "jump", "longstrider",
        "purify_food_and_drink", "speak_with_animals", "thunderwave",
        "animal_messenger", "barkskin", "darkvision", "enhance_ability",
        "find_traps", "flame_blade", "flaming_sphere", "gust_of_wind",
        "heat_metal", "hold_person", "lesser_restoration",
        "locate_animals_or_plants", "locate_object", "moonbeam",
        "pass_without_trace", "protection_from_poison", "spike_growth",
    ),
    "paladin": (
        "bless", "command", "cure_wounds", "detect_evil_and_good",
        "detect_magic", "detect_poison_and_disease", "divine_favor", "heroism",
        "protection_from_evil_and_good", "purify_food_and_drink",
        "shield_of_faith", "aid", "branding_smite", "find_steed",
        "lesser_restoration", "locate_object", "magic_weapon",
        "protection_from_poison", "zone_of_truth",
    ),
    "ranger": (
        "alarm", "animal_friendship", "cure_wounds", "detect_magic",
        "detect_poison_and_disease", "fog_cloud", "goodberry", "hunters_mark",
        "jump", "longstrider", "speak_with_animals", "animal_messenger",
        "barkskin", "darkvision", "find_traps", "lesser_restoration",
        "locate_animals_or_plants", "locate_object", "pass_without_trace",
        "protection_from_poison", "silence", "spike_growth",
    ),
    "sorcerer": (
        "acid_splash", "chill_touch", "dancing_lights", "fire_bolt", "light",
        "mage_hand", "mending", "message", "minor_illusion", "poison_spray",
        "prestidigitation", "ray_of_frost", "shocking_grasp", "true_strike",
        "burning_hands", "charm_person", "color_spray", "comprehend_languages",
        "detect_magic", "disguise_self", "expeditious_retreat", "false_life",
        "feather_fall", "fog_cloud", "jump", "mage_armor", "magic_missile",
        "shield", "silent_image", "sleep", "thunderwave", "alter_self",
        "blindness_deafness", "blur", "darkness", "darkvision",
        "detect_thoughts", "enhance_ability", "enlarge_reduce", "gust_of_wind",
        "hold_person", "invisibility", "knock", "levitate", "mirror_image",
        "misty_step", "scorching_ray", "see_invisibility", "shatter",
        "spider_climb", "suggestion", "web",
    ),
    "warlock": (
        "chill_touch", "eldritch_blast", "mage_hand", "minor_illusion",
        "poison_spray", "prestidigitation", "true_strike", "charm_person",
        "comprehend_languages", "expeditious_retreat", "hellish_rebuke",
        "illusory_script", "protection_from_evil_and_good", "unseen_servant",
        "darkness", "enthrall", "hold_person", "invisibility", "mirror_image",
        "misty_step", "ray_of_enfeeblement", "shatter", "spider_climb",
        "suggestion",
    ),
    "wizard": (
        "acid_splash", "chill_touch", "dancing_lights", "fire_bolt", "light",
        "mage_hand", "mending", "message", "minor_illusion", "poison_spray",
        "prestidigitation", "ray_of_frost", "shocking_grasp", "true_strike",
        "alarm", "burning_hands", "charm_person", "color_spray",
        "comprehend_languages", "detect_magic", "disguise_self",
        "expeditious_retreat", "false_life", "feather_fall", "find_familiar",
        "floating_disk", "fog_cloud", "grease", "hideous_laughter", "identify",
        "illusory_script", "jump", "longstrider", "mage_armor", "magic_missile",
        "protection_from_evil_and_good", "shield", "silent_image", "sleep",
        "thunderwave", "unseen_servant", "acid_arrow", "alter_self",
        "arcane_lock", "arcanists_magic_aura", "blindness_deafness", "blur",
        "continual_flame", "darkness", "darkvision", "detect_thoughts",
        "enlarge_reduce", "flaming_sphere", "gentle_repose", "gust_of_wind",
        "hold_person", "invisibility", "knock", "levitate", "locate_object",
        "magic_mouth", "magic_weapon", "mirror_image", "misty_step",
        "ray_of_enfeeblement", "rope_trick", "scorching_ray",
        "see_invisibility", "shatter", "spider_climb", "suggestion", "web",
    ),
}


@dataclass(frozen=True, slots=True)
class SrdCharacterCoverage:
    missing_species_ids: tuple[str, ...]
    missing_class_ids: tuple[str, ...]
    missing_subclass_ids: tuple[str, ...]
    missing_spell_ids: tuple[str, ...]
    missing_class_spell_ids: tuple[str, ...]
    unexpected_spell_levels: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return not any(
            (
                self.missing_species_ids,
                self.missing_class_ids,
                self.missing_subclass_ids,
                self.missing_spell_ids,
                self.missing_class_spell_ids,
                self.unexpected_spell_levels,
            )
        )


def audit_srd_character_coverage(
    catalog: CharacterCatalog,
    spells_root: str | Path,
) -> SrdCharacterCoverage:
    """Compare data-driven character content with the complete level-3 target."""
    species_ids = {definition.id for definition in catalog.species}
    classes = {definition.id: definition for definition in catalog.classes}
    subclass_ids = {
        subclass.id
        for definition in catalog.classes
        for subclass in definition.subclass_choices
    }
    expected_spells = {
        spell_id
        for spell_ids in SRD_SPELL_IDS_BY_LEVEL.values()
        for spell_id in spell_ids
    }
    actual_levels: dict[str, int] = {}
    for path in Path(spells_root).glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        spell_id = raw.get("id")
        level = raw.get("level")
        if isinstance(spell_id, str) and isinstance(level, int):
            actual_levels[spell_id] = level
    expected_levels = {
        spell_id: level
        for level, spell_ids in SRD_SPELL_IDS_BY_LEVEL.items()
        for spell_id in spell_ids
    }
    return SrdCharacterCoverage(
        missing_species_ids=tuple(sorted(set(SRD_SPECIES_IDS) - species_ids)),
        missing_class_ids=tuple(sorted(set(SRD_CLASS_SUBCLASS_IDS) - set(classes))),
        missing_subclass_ids=tuple(
            sorted(set(SRD_CLASS_SUBCLASS_IDS.values()) - subclass_ids)
        ),
        missing_spell_ids=tuple(sorted(expected_spells - set(actual_levels))),
        missing_class_spell_ids=tuple(
            sorted(
                f"{class_id}:{spell_id}"
                for class_id, expected_ids in SRD_CLASS_SPELL_IDS.items()
                for spell_id in expected_ids
                if class_id not in classes
                or spell_id
                not in {
                    *classes[class_id].cantrip_choices,
                    *classes[class_id].spell_choices,
                }
            )
        ),
        unexpected_spell_levels=tuple(
            sorted(
                spell_id
                for spell_id, expected_level in expected_levels.items()
                if spell_id in actual_levels
                and actual_levels[spell_id] != expected_level
            )
        ),
    )


__all__ = [
    "SRD_CLASS_SUBCLASS_IDS",
    "SRD_CLASS_SPELL_IDS",
    "SRD_SPECIES_IDS",
    "SRD_SPELL_IDS_BY_LEVEL",
    "SrdCharacterCoverage",
    "audit_srd_character_coverage",
]
