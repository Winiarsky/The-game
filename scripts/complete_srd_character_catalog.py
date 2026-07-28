#!/usr/bin/env python3
"""Materialize the complete SRD 5.1 class catalog through character level 3."""

from __future__ import annotations

import json
from pathlib import Path

from dnd_board_game.character_creation.srd_manifest import (
    SRD_CLASS_SPELL_IDS,
    SRD_SPELL_IDS_BY_LEVEL,
)


CATALOG = Path("content/character_creation/catalog.json")
CANTRIPS = set(SRD_SPELL_IDS_BY_LEVEL[0])
ALL_SKILLS = [
    "acrobatics", "animal_handling", "arcana", "athletics", "deception",
    "history", "insight", "intimidation", "investigation", "medicine",
    "nature", "perception", "performance", "persuasion", "religion",
    "sleight_of_hand", "stealth", "survival",
]


def _spells(class_id: str) -> tuple[list[str], list[str]]:
    values = SRD_CLASS_SPELL_IDS[class_id]
    return (
        [spell_id for spell_id in values if spell_id in CANTRIPS],
        [spell_id for spell_id in values if spell_id not in CANTRIPS],
    )


def _package(
    package_id: str,
    label: str,
    *items: str | tuple[str, int, bool] | tuple[str, int, bool, bool],
) -> list[dict[str, object]]:
    grants: list[dict[str, object]] = []
    for index, item in enumerate(items):
        if isinstance(item, tuple):
            item_id, quantity, equipped = item[:3]
            separate_instances = bool(item[3]) if len(item) == 4 else False
        else:
            item_id, quantity, equipped = item, 1, index < 3
            separate_instances = False
        grant: dict[str, object] = {
            "item_id": item_id,
            "equipped": equipped,
        }
        if quantity != 1:
            grant["quantity"] = quantity
        if separate_instances:
            grant["separate_instances"] = True
        grants.append(grant)
    return [{
        "id": package_id,
        "label": label,
        "items": grants,
    }]


def _class_definitions() -> dict[str, dict[str, object]]:
    bard_cantrips, bard_spells = _spells("bard")
    druid_cantrips, druid_spells = _spells("druid")
    paladin_cantrips, paladin_spells = _spells("paladin")
    ranger_cantrips, ranger_spells = _spells("ranger")
    sorcerer_cantrips, sorcerer_spells = _spells("sorcerer")
    warlock_cantrips, warlock_spells = _spells("warlock")
    return {
        "bard": {
            "id": "bard", "name": "Bard", "hit_die": 8,
            "saving_throw_proficiencies": ["dexterity", "charisma"],
            "skill_choice_count": 3, "skill_choices": ALL_SKILLS,
            "weapon_proficiencies": ["simple", "hand_crossbow", "longsword", "rapier", "shortsword"],
            "armor_proficiencies": ["light"],
            "feature_ids": ["spellcasting", "bardic_inspiration"],
            "expertise_choice_count": 2, "expertise_choice_level": 3,
            "spellcasting_ability": "charisma",
            "cantrip_choice_count": 2, "cantrip_choices": bard_cantrips,
            "spell_choice_count": 4, "spell_choices": bard_spells,
            "spell_slots": {"1": 2}, "preparation_kind": "known",
            "level_progression": [
                {"level": 2, "feature_ids": ["jack_of_all_trades", "song_of_rest"], "spell_slots": {"1": 3}, "spell_choice_count": 5},
                {"level": 3, "feature_ids": ["bard_college"], "spell_slots": {"1": 4, "2": 2}, "spell_choice_count": 6},
            ],
            "subclass_choice_count": 1, "subclass_choice_level": 3,
            "subclass_choices": [{"id": "college_of_lore", "name": "College of Lore", "feature_ids": ["bonus_proficiencies", "cutting_words"]}],
            "choice_groups": [
                {
                    "id": "bard_instruments", "name": "Musical Instruments", "level": 1, "choice_count": 3,
                    "options": [
                        {"id": f"bard_instrument_{instrument}", "name": instrument.replace("_", " ").title(), "tool_proficiencies": [instrument]}
                        for instrument in ("bagpipes", "drum", "dulcimer", "flute", "lute", "lyre", "horn", "pan_flute", "shawm", "viol")
                    ],
                },
                {
                    "id": "lore_bonus_proficiencies", "name": "Bonus Proficiencies", "level": 3, "choice_count": 3,
                    "options": [
                        {"id": f"lore_skill_{skill}", "name": skill.replace("_", " ").title(), "skill_proficiencies": [skill]}
                        for skill in ALL_SKILLS
                    ],
                },
            ],
            "equipment_packages": _package("bard_diplomat", "Rapier i wyposażenie dyplomaty", "rapier", "leather_armor", "lute", "dagger", "diplomats_pack"),
        },
        "druid": {
            "id": "druid", "name": "Druid", "hit_die": 8,
            "saving_throw_proficiencies": ["intelligence", "wisdom"],
            "skill_choice_count": 2,
            "skill_choices": ["arcana", "animal_handling", "insight", "medicine", "nature", "perception", "religion", "survival"],
            "weapon_proficiencies": ["club", "dagger", "dart", "javelin", "mace", "quarterstaff", "scimitar", "sickle", "sling", "spear"],
            "armor_proficiencies": ["light", "medium", "shield"],
            "tool_proficiencies": ["herbalism_kit"],
            "feature_ids": ["druidic", "spellcasting"],
            "spellcasting_ability": "wisdom",
            "cantrip_choice_count": 2, "cantrip_choices": druid_cantrips,
            "spell_choice_count": 0, "spell_choices": druid_spells,
            "spell_slots": {"1": 2}, "preparation_kind": "prepared",
            "preparation_formula": "ability_modifier_plus_level",
            "level_progression": [
                {"level": 2, "feature_ids": ["wild_shape", "druid_circle"], "spell_slots": {"1": 3}, "cantrip_choice_count": 3},
                {"level": 3, "spell_slots": {"1": 4, "2": 2}},
            ],
            "subclass_choice_count": 1, "subclass_choice_level": 2,
            "subclass_choices": [{"id": "circle_of_the_land", "name": "Circle of the Land", "feature_ids": ["bonus_cantrip", "natural_recovery"]}],
            "choice_groups": [{
                "id": "circle_land", "name": "Circle Land", "level": 2, "choice_count": 1,
                "options": [
                    {
                        "id": f"circle_land_{terrain}",
                        "name": terrain.title(),
                        "feature_ids": [f"circle_land_{terrain}"],
                        "level_progression": [{"level": 3, "always_prepared_spell_ids": spells}],
                    }
                    for terrain, spells in {
                        "arctic": ["hold_person", "spike_growth"],
                        "coast": ["mirror_image", "misty_step"],
                        "desert": ["blur", "silence"],
                        "forest": ["barkskin", "spider_climb"],
                        "grassland": ["invisibility", "pass_without_trace"],
                        "mountain": ["spider_climb", "spike_growth"],
                        "swamp": ["darkness", "acid_arrow"],
                        "underdark": ["spider_climb", "web"],
                    }.items()
                ],
            }],
            "equipment_packages": _package("druid_explorer", "Scimitar, tarcza i focus druida", "scimitar", "shield", "leather_armor", "druidic_focus_mistletoe", "explorers_pack"),
        },
        "paladin": {
            "id": "paladin", "name": "Paladyn", "hit_die": 10,
            "saving_throw_proficiencies": ["wisdom", "charisma"],
            "skill_choice_count": 2,
            "skill_choices": ["athletics", "insight", "intimidation", "medicine", "persuasion", "religion"],
            "weapon_proficiencies": ["simple", "martial"],
            "armor_proficiencies": ["light", "medium", "heavy", "shield"],
            "feature_ids": ["divine_sense", "lay_on_hands"],
            "fighting_style_choice_level": 2,
            "fighting_style_choices": ["defense", "dueling", "great_weapon_fighting", "protection"],
            "spellcasting_ability": "charisma", "spellcasting_level": 2,
            "cantrip_choice_count": 0, "cantrip_choices": paladin_cantrips,
            "spell_choice_count": 0, "spell_choices": paladin_spells,
            "spell_slots": {}, "preparation_kind": "prepared",
            "preparation_formula": "ability_modifier_plus_half_level",
            "level_progression": [
                {"level": 2, "feature_ids": ["fighting_style", "spellcasting", "divine_smite"], "spell_slots": {"1": 2}},
                {"level": 3, "feature_ids": ["divine_health", "sacred_oath"], "spell_slots": {"1": 3}},
            ],
            "subclass_choice_count": 1, "subclass_choice_level": 3,
            "subclass_choices": [{
                "id": "oath_of_devotion", "name": "Oath of Devotion",
                "feature_ids": ["channel_divinity_sacred_weapon", "channel_divinity_turn_the_unholy"],
                "always_prepared_spell_ids": ["protection_from_evil_and_good", "sanctuary"],
            }],
            "equipment_packages": _package("paladin_guardian", "Miecz, tarcza i kolczuga", "longsword", "shield", "chain_mail", ("javelin", 5, False), "holy_symbol_amulet", "priests_pack"),
        },
        "ranger": {
            "id": "ranger", "name": "Łowca", "hit_die": 10,
            "saving_throw_proficiencies": ["strength", "dexterity"],
            "skill_choice_count": 3,
            "skill_choices": ["animal_handling", "athletics", "insight", "investigation", "nature", "perception", "stealth", "survival"],
            "weapon_proficiencies": ["simple", "martial"],
            "armor_proficiencies": ["light", "medium", "shield"],
            "feature_ids": ["favored_enemy", "natural_explorer"],
            "fighting_style_choice_level": 2,
            "fighting_style_choices": ["archery", "defense", "dueling", "two_weapon_fighting"],
            "spellcasting_ability": "wisdom", "spellcasting_level": 2,
            "cantrip_choice_count": 0, "cantrip_choices": ranger_cantrips,
            "spell_choice_count": 0, "spell_choices": ranger_spells,
            "spell_slots": {}, "preparation_kind": "known",
            "level_progression": [
                {"level": 2, "feature_ids": ["fighting_style", "spellcasting"], "spell_slots": {"1": 2}, "spell_choice_count": 2},
                {"level": 3, "feature_ids": ["ranger_archetype", "primeval_awareness"], "spell_slots": {"1": 3}, "spell_choice_count": 3},
            ],
            "subclass_choice_count": 1, "subclass_choice_level": 3,
            "subclass_choices": [{"id": "hunter", "name": "Hunter", "feature_ids": ["hunters_prey"]}],
            "choice_groups": [
                {
                    "id": "favored_enemy", "name": "Favored Enemy", "level": 1, "choice_count": 1,
                    "options": [
                        {"id": f"favored_enemy_{creature_type}", "name": creature_type.replace("_", " ").title(), "feature_ids": [f"favored_enemy_{creature_type}"]}
                        for creature_type in (
                            "aberration", "beast", "celestial", "construct",
                            "dragon", "elemental", "fey", "fiend", "giant",
                            "humanoid", "monstrosity", "ooze", "plant", "undead",
                        )
                    ],
                },
                {
                    "id": "natural_explorer", "name": "Natural Explorer", "level": 1, "choice_count": 1,
                    "options": [
                        {"id": f"natural_explorer_{terrain}", "name": terrain.replace("_", " ").title(), "feature_ids": [f"natural_explorer_{terrain}"]}
                        for terrain in (
                            "arctic", "coast", "desert", "forest", "grassland",
                            "mountain", "swamp", "underdark",
                        )
                    ],
                },
                {
                    "id": "hunters_prey", "name": "Hunter’s Prey", "level": 3, "choice_count": 1,
                    "options": [
                        {"id": "colossus_slayer", "name": "Colossus Slayer", "feature_ids": ["colossus_slayer"]},
                        {"id": "giant_killer", "name": "Giant Killer", "feature_ids": ["giant_killer"]},
                        {"id": "horde_breaker", "name": "Horde Breaker", "feature_ids": ["horde_breaker"]},
                    ],
                },
            ],
            "equipment_packages": _package("ranger_archer", "Łuk, dwa miecze i zbroja łuskowa", "longbow", ("shortsword", 2, True, True), "scale_mail", ("arrow", 20, False), "explorers_pack"),
        },
        "sorcerer": {
            "id": "sorcerer", "name": "Zaklinacz", "hit_die": 6,
            "saving_throw_proficiencies": ["constitution", "charisma"],
            "skill_choice_count": 2,
            "skill_choices": ["arcana", "deception", "insight", "intimidation", "persuasion", "religion"],
            "weapon_proficiencies": ["dagger", "dart", "sling", "quarterstaff", "crossbow"],
            "feature_ids": ["spellcasting", "sorcerous_origin"],
            "spellcasting_ability": "charisma",
            "cantrip_choice_count": 4, "cantrip_choices": sorcerer_cantrips,
            "spell_choice_count": 2, "spell_choices": sorcerer_spells,
            "spell_slots": {"1": 2}, "preparation_kind": "known",
            "level_progression": [
                {"level": 2, "feature_ids": ["font_of_magic"], "spell_slots": {"1": 3}, "spell_choice_count": 3},
                {"level": 3, "feature_ids": ["metamagic"], "spell_slots": {"1": 4, "2": 2}, "spell_choice_count": 4},
            ],
            "subclass_choice_count": 1, "subclass_choice_level": 1,
            "subclass_choices": [{"id": "draconic_bloodline", "name": "Draconic Bloodline", "feature_ids": ["dragon_ancestor", "draconic_resilience"]}],
            "choice_groups": [{
                "id": "metamagic", "name": "Metamagic", "level": 3, "choice_count": 2,
                "options": [
                    {"id": "careful_spell", "name": "Careful Spell", "feature_ids": ["metamagic_careful"]},
                    {"id": "distant_spell", "name": "Distant Spell", "feature_ids": ["metamagic_distant"]},
                    {"id": "empowered_spell", "name": "Empowered Spell", "feature_ids": ["metamagic_empowered"]},
                    {"id": "extended_spell", "name": "Extended Spell", "feature_ids": ["metamagic_extended"]},
                    {"id": "heightened_spell", "name": "Heightened Spell", "feature_ids": ["metamagic_heightened"]},
                    {"id": "quickened_spell", "name": "Quickened Spell", "feature_ids": ["metamagic_quickened"]},
                    {"id": "subtle_spell", "name": "Subtle Spell", "feature_ids": ["metamagic_subtle"]},
                    {"id": "twinned_spell", "name": "Twinned Spell", "feature_ids": ["metamagic_twinned"]},
                ],
            }],
            "equipment_packages": _package("sorcerer_explorer", "Kusza i focus mistyczny", "crossbow", "dagger", "arcane_focus_crystal", ("crossbow_bolt", 20, False), "explorers_pack"),
        },
        "warlock": {
            "id": "warlock", "name": "Czarnoksiężnik", "hit_die": 8,
            "saving_throw_proficiencies": ["wisdom", "charisma"],
            "skill_choice_count": 2,
            "skill_choices": ["arcana", "deception", "history", "intimidation", "investigation", "nature", "religion"],
            "weapon_proficiencies": ["simple"], "armor_proficiencies": ["light"],
            "feature_ids": ["otherworldly_patron", "pact_magic"],
            "spellcasting_ability": "charisma",
            "cantrip_choice_count": 2, "cantrip_choices": warlock_cantrips,
            "spell_choice_count": 2, "spell_choices": warlock_spells,
            "spell_slots": {"1": 1}, "spell_slot_recovery": "short_rest",
            "preparation_kind": "known",
            "level_progression": [
                {"level": 2, "feature_ids": ["eldritch_invocations"], "spell_slots": {"1": 2}, "spell_choice_count": 3},
                {"level": 3, "feature_ids": ["pact_boon"], "spell_slots": {"2": 2}, "spell_choice_count": 4},
            ],
            "subclass_choice_count": 1, "subclass_choice_level": 1,
            "subclass_choices": [{
                "id": "the_fiend", "name": "The Fiend",
                "feature_ids": ["dark_ones_blessing"],
                "additional_spell_choice_ids": ["burning_hands", "command"],
                "level_progression": [{"level": 3, "additional_spell_choice_ids": ["blindness_deafness", "scorching_ray"]}],
            }],
            "choice_groups": [
                {
                    "id": "eldritch_invocations", "name": "Eldritch Invocations", "level": 2, "choice_count": 2,
                    "options": [
                        {"id": "agonizing_blast", "name": "Agonizing Blast", "feature_ids": ["agonizing_blast"]},
                        {"id": "armor_of_shadows", "name": "Armor of Shadows", "feature_ids": ["armor_of_shadows"], "at_will_spell_ids": ["mage_armor"]},
                        {"id": "beast_speech", "name": "Beast Speech", "feature_ids": ["beast_speech"], "at_will_spell_ids": ["speak_with_animals"]},
                        {"id": "beguiling_influence", "name": "Beguiling Influence", "feature_ids": ["beguiling_influence"], "skill_proficiencies": ["deception", "persuasion"]},
                        {"id": "devils_sight", "name": "Devil’s Sight", "feature_ids": ["devils_sight"]},
                        {"id": "eldritch_sight", "name": "Eldritch Sight", "feature_ids": ["eldritch_sight"], "at_will_spell_ids": ["detect_magic"]},
                        {"id": "fiendish_vigor", "name": "Fiendish Vigor", "feature_ids": ["fiendish_vigor"], "at_will_spell_ids": ["false_life"]},
                        {"id": "mask_of_many_faces", "name": "Mask of Many Faces", "feature_ids": ["mask_of_many_faces"], "at_will_spell_ids": ["disguise_self"]},
                        {"id": "misty_visions", "name": "Misty Visions", "feature_ids": ["misty_visions"], "at_will_spell_ids": ["silent_image"]},
                        {"id": "repelling_blast", "name": "Repelling Blast", "feature_ids": ["repelling_blast"]},
                    ],
                },
                {
                    "id": "pact_boon", "name": "Pact Boon", "level": 3, "choice_count": 1,
                    "options": [
                        {"id": "pact_of_the_chain", "name": "Pact of the Chain", "feature_ids": ["pact_of_the_chain"], "ritual_spell_ids": ["find_familiar"]},
                        {"id": "pact_of_the_blade", "name": "Pact of the Blade", "feature_ids": ["pact_of_the_blade"]},
                        {"id": "pact_of_the_tome", "name": "Pact of the Tome", "feature_ids": ["pact_of_the_tome"], "cantrip_choice_count": 3, "cantrip_choices": list(SRD_SPELL_IDS_BY_LEVEL[0])},
                    ],
                },
            ],
            "equipment_packages": _package("warlock_scholar", "Kusza, skórznia i focus", "crossbow", "leather_armor", "arcane_focus_crystal", "dagger", ("crossbow_bolt", 20, False), "scholars_pack"),
        },
    }


def main() -> None:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    species = {entry["id"]: entry for entry in data["species"]}
    wizard_cantrips, _ = _spells("wizard")
    species["elf"]["cantrip_choice_count"] = 1
    species["elf"]["cantrip_choices"] = wizard_cantrips
    species["elf"]["cantrip_ability"] = "intelligence"
    species["tiefling"]["fixed_cantrip_ids"] = ["thaumaturgy"]
    species["tiefling"]["cantrip_ability"] = "charisma"
    species["tiefling"]["innate_spells"] = [
        {
            "spell_id": "hellish_rebuke",
            "level": 2,
            "resource_id": "infernal_legacy_hellish_rebuke",
            "recovery": "long_rest",
        },
        {
            "spell_id": "darkness",
            "level": 3,
            "resource_id": "infernal_legacy_darkness",
            "recovery": "long_rest",
        },
    ]
    data["species"] = list(species.values())
    classes = {entry["id"]: entry for entry in data["classes"]}
    classes.update(_class_definitions())
    for class_id in ("cleric", "wizard"):
        cantrips, spells = _spells(class_id)
        classes[class_id]["cantrip_choices"] = cantrips
        classes[class_id]["spell_choices"] = spells
    classes["cleric"]["cantrip_choice_count"] = 3
    classes["cleric"]["subclass_choices"][0]["always_prepared_spell_ids"] = ["bless", "cure_wounds"]
    classes["cleric"]["subclass_choices"][0]["level_progression"] = [
        {
            "level": 2,
            "feature_ids": ["channel_divinity_preserve_life"],
        },
        {
            "level": 3,
            "always_prepared_spell_ids": [
                "lesser_restoration",
                "spiritual_weapon",
            ],
        },
    ]
    classes["wizard"]["cantrip_choice_count"] = 3
    classes["wizard"]["level_progression"][0]["spell_choice_count"] = 8
    classes["wizard"]["level_progression"][1]["spell_choice_count"] = 10
    for package in classes["rogue"]["equipment_packages"]:
        for item in package["items"]:
            if item["item_id"] == "dagger" and int(item.get("quantity", 1)) > 1:
                item["separate_instances"] = True
    data["classes"] = [
        classes[class_id]
        for class_id in (
            "barbarian", "bard", "cleric", "druid", "fighter", "monk",
            "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard",
        )
    ]
    CATALOG.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
