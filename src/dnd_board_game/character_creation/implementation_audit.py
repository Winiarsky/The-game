"""Executable completeness audit for the SRD character target through level 3.

The catalogue audit proves that content exists.  This module additionally
requires every granted feature to have an explicit runtime contract, including
features intentionally resolved at the physical table.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
import json

from .models import CharacterCatalog
from .srd_manifest import SRD_SPELL_IDS_BY_LEVEL


class FeatureImplementationKind(StrEnum):
    EXECUTABLE = "executable"
    DATA_DRIVEN = "data_driven"
    MARKER = "marker"
    TABLE_ASSISTED = "table_assisted"


_MARKER_FEATURE_IDS = frozenset(
    {
        "arcane_tradition",
        "bard_college",
        "divine_domain",
        "druid_circle",
        "eldritch_invocations",
        "fighting_style",
        "hunters_prey",
        "martial_archetype",
        "metamagic",
        "monastic_tradition",
        "otherworldly_patron",
        "pact_boon",
        "primal_path",
        "ranger_archetype",
        "roguish_archetype",
        "sacred_oath",
        "sorcerous_origin",
    }
)

_TABLE_ASSISTED_FEATURES = {
    "druidic": (
        "Sekretny język działa w rozmowie i na fizycznych notatkach; aplikacja "
        "przechowuje uprawnienie, a treść komunikatu ustalają gracze."
    ),
    "thieves_cant": (
        "Kodowany język działa w rozmowie i na fizycznych notatkach; aplikacja "
        "przechowuje uprawnienie, a znaczenie deklarują gracze."
    ),
    "pact_of_the_chain": (
        "Aplikacja przyznaje rytuał Find Familiar i rozlicza koszt/czas. "
        "Specjalną formę, telepatię i samodzielne zachowanie chowańca prowadzi stół."
    ),
    "tinker": (
        "Trzy drobne mechaniczne urządzenia są rekwizytami fabularnymi bez "
        "uniwersalnego skutku mechanicznego; aplikacja przechowuje cechę."
    ),
}

_TABLE_ASSISTED_FEATURE_RIDERS = {
    "cutting_words": (
        "Reakcja przeciw rzutowi ataku ma pełne okno runtime. Użycie przeciw "
        "fizycznemu ability checkowi albo osobnemu rzutowi obrażeń pozostaje "
        "jawną korektą wyniku przy stole."
    ),
}

_DATA_DRIVEN_FEATURE_IDS = frozenset(
    {
        "armor_of_shadows",
        "beast_speech",
        "beguiling_influence",
        "bonus_cantrip",
        "bonus_proficiencies",
        "circle_land_arctic",
        "circle_land_coast",
        "circle_land_desert",
        "circle_land_forest",
        "circle_land_grassland",
        "circle_land_mountain",
        "circle_land_swamp",
        "circle_land_underdark",
        "darkvision",
        "dragon_ancestor",
        "dwarven_speed",
        "elf_weapon_training",
        "eldritch_sight",
        "evocation_savant",
        "expertise",
        "favored_enemy",
        "favored_enemy_aberration",
        "favored_enemy_beast",
        "favored_enemy_celestial",
        "favored_enemy_construct",
        "favored_enemy_dragon",
        "favored_enemy_elemental",
        "favored_enemy_fey",
        "favored_enemy_fiend",
        "favored_enemy_giant",
        "favored_enemy_humanoid",
        "favored_enemy_monstrosity",
        "favored_enemy_ooze",
        "favored_enemy_plant",
        "favored_enemy_undead",
        "fiendish_vigor",
        "high_elf_cantrip",
        "human_versatility",
        "infernal_legacy",
        "life_domain",
        "mask_of_many_faces",
        "misty_visions",
        "natural_explorer",
        "natural_explorer_arctic",
        "natural_explorer_coast",
        "natural_explorer_desert",
        "natural_explorer_forest",
        "natural_explorer_grassland",
        "natural_explorer_mountain",
        "natural_explorer_swamp",
        "natural_explorer_underdark",
        "pact_magic",
        "pact_of_the_tome",
        "skill_versatility",
        "sneak_attack_2d6",
        "spellcasting",
    }
)

_EXECUTABLE_FEATURE_IDS = frozenset(
    {
        "action_surge",
        "agonizing_blast",
        "arcane_recovery",
        "artificers_lore",
        "bardic_inspiration",
        "brave",
        "breath_weapon",
        "breath_weapon_acid_line_dex",
        "breath_weapon_cold_cone_con",
        "breath_weapon_fire_cone_dex",
        "breath_weapon_fire_line_dex",
        "breath_weapon_lightning_line_dex",
        "breath_weapon_poison_cone_con",
        "channel_divinity",
        "channel_divinity_preserve_life",
        "channel_divinity_sacred_weapon",
        "channel_divinity_turn_the_unholy",
        "colossus_slayer",
        "cunning_action",
        "cutting_words",
        "damage_resistance_acid",
        "damage_resistance_cold",
        "damage_resistance_fire",
        "damage_resistance_lightning",
        "damage_resistance_poison",
        "danger_sense",
        "dark_ones_blessing",
        "deflect_missiles",
        "devils_sight",
        "disciple_of_life",
        "divine_health",
        "divine_sense",
        "divine_smite",
        "draconic_resilience",
        "dwarven_resilience",
        "dwarven_toughness",
        "fast_hands",
        "fey_ancestry",
        "font_of_magic",
        "frenzy",
        "giant_killer",
        "gnome_cunning",
        "halfling_nimbleness",
        "hellish_resistance",
        "horde_breaker",
        "improved_critical",
        "jack_of_all_trades",
        "ki",
        "lay_on_hands",
        "lucky",
        "martial_arts",
        "metamagic_careful",
        "metamagic_distant",
        "metamagic_empowered",
        "metamagic_extended",
        "metamagic_heightened",
        "metamagic_quickened",
        "metamagic_subtle",
        "metamagic_twinned",
        "natural_recovery",
        "naturally_stealthy",
        "open_hand_technique",
        "pact_of_the_blade",
        "primeval_awareness",
        "rage",
        "reckless_attack",
        "relentless_endurance",
        "repelling_blast",
        "savage_attacks",
        "sculpt_spells",
        "second_story_work",
        "second_wind",
        "sneak_attack",
        "song_of_rest",
        "stonecunning",
        "trance",
        "turn_undead",
        "unarmored_defense_constitution",
        "unarmored_defense_wisdom",
        "unarmored_movement_10",
        "wild_shape",
    }
)


def feature_implementation_kind(
    feature_id: str,
) -> FeatureImplementationKind | None:
    if feature_id.startswith("favored_enemy_humanoid_race_"):
        return FeatureImplementationKind.DATA_DRIVEN
    if feature_id in _EXECUTABLE_FEATURE_IDS:
        return FeatureImplementationKind.EXECUTABLE
    if feature_id in _DATA_DRIVEN_FEATURE_IDS:
        return FeatureImplementationKind.DATA_DRIVEN
    if feature_id in _MARKER_FEATURE_IDS:
        return FeatureImplementationKind.MARKER
    if feature_id in _TABLE_ASSISTED_FEATURES:
        return FeatureImplementationKind.TABLE_ASSISTED
    return None


def catalog_feature_ids(catalog: CharacterCatalog) -> frozenset[str]:
    feature_ids: set[str] = set()
    for species in catalog.species:
        feature_ids.update(species.trait_ids)
        for variant in species.variant_choices:
            feature_ids.update(variant.trait_ids)
    for class_definition in catalog.classes:
        feature_ids.update(class_definition.feature_ids)
        for level in class_definition.level_progression:
            feature_ids.update(level.feature_ids)
        for subclass in class_definition.subclass_choices:
            feature_ids.update(subclass.feature_ids)
            for level in subclass.level_progression:
                feature_ids.update(level.feature_ids)
        for group in class_definition.choice_groups:
            for option in group.options:
                feature_ids.update(option.feature_ids)
    return frozenset(feature_ids)


@dataclass(frozen=True, slots=True)
class CharacterImplementationAudit:
    feature_ids: frozenset[str]
    missing_feature_ids: tuple[str, ...]
    spell_count: int
    executable_spell_count: int
    table_assisted_spell_count: int
    malformed_assisted_spell_ids: tuple[str, ...]
    unsupported_spell_effect_ids: tuple[str, ...]

    @property
    def complete(self) -> bool:
        return (
            not self.missing_feature_ids
            and not self.malformed_assisted_spell_ids
            and not self.unsupported_spell_effect_ids
            and self.spell_count
            == self.executable_spell_count + self.table_assisted_spell_count
        )


def audit_character_implementation(
    catalog: CharacterCatalog,
    spells_root: str | Path,
) -> CharacterImplementationAudit:
    feature_ids = catalog_feature_ids(catalog)
    spell_count = 0
    executable_spell_count = 0
    table_assisted_spell_count = 0
    malformed_assisted: list[str] = []
    unsupported_effects: list[str] = []
    supported_combat_actions = {
        "concentration_attack_bonus",
        "long_cast_effect",
        "multi_target_damage",
        "targeted_status",
        "reaction_ac_bonus",
        "reaction_damage",
        "spell_counter",
        "spell_debuff",
        "spell_dispel",
        "spell_movement",
        "stabilize",
        "summon",
    }
    target_spell_ids = {
        spell_id
        for spell_ids in SRD_SPELL_IDS_BY_LEVEL.values()
        for spell_id in spell_ids
    }
    for path in Path(spells_root).glob("*.json"):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("id") not in target_spell_ids:
            continue
        effect = raw.get("effect", {})
        if not isinstance(effect, dict):
            continue
        spell_count += 1
        effect_kind = effect.get("kind")
        if effect_kind == "assisted":
            table_assisted_spell_count += 1
            if (
                effect.get("action_type") != "assisted_spell"
                or effect.get("resolution_mode") not in {"tabletop", "narrative"}
                or not str(effect.get("instructions", "")).strip()
            ):
                malformed_assisted.append(str(raw.get("id", path.stem)))
        else:
            executable_spell_count += 1
            if effect_kind not in {
                "attack",
                "combat_action",
                "exploration",
                "healing",
            } or (
                effect_kind == "combat_action"
                and effect.get("action_type") not in supported_combat_actions
            ):
                unsupported_effects.append(str(raw.get("id", path.stem)))
    return CharacterImplementationAudit(
        feature_ids=feature_ids,
        missing_feature_ids=tuple(
            sorted(
                feature_id
                for feature_id in feature_ids
                if feature_implementation_kind(feature_id) is None
            )
        ),
        spell_count=spell_count,
        executable_spell_count=executable_spell_count,
        table_assisted_spell_count=table_assisted_spell_count,
        malformed_assisted_spell_ids=tuple(sorted(malformed_assisted)),
        unsupported_spell_effect_ids=tuple(sorted(unsupported_effects)),
    )


def table_assisted_feature_exceptions() -> dict[str, str]:
    return dict(_TABLE_ASSISTED_FEATURES)


def table_assisted_feature_riders() -> dict[str, str]:
    """Return table-owned clauses of otherwise executable features."""
    return dict(_TABLE_ASSISTED_FEATURE_RIDERS)


__all__ = [
    "CharacterImplementationAudit",
    "FeatureImplementationKind",
    "audit_character_implementation",
    "catalog_feature_ids",
    "feature_implementation_kind",
    "table_assisted_feature_exceptions",
    "table_assisted_feature_riders",
]
