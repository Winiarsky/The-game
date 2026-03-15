from __future__ import annotations

from statuses.base import Status

WIZARD_KEY_ABILITY_CHOICES = ["intelligence"]
WIZARD_ARCANE_SCHOOL_CHOICES = [
    "abjuration",
    "conjuration",
    "divination",
    "enchantment",
    "evocation",
    "illusion",
    "necromancy",
    "transmutation",
]
WIZARD_ARCANE_STUDY_CHOICES = list(WIZARD_ARCANE_SCHOOL_CHOICES) + ["universalist"]
WIZARD_ARCANE_THESIS_CHOICES = [
    "improved_familiar_attunement",
    "metamagical_experimentation",
    "spell_blending",
    "spell_substitution",
]
WIZARD_FEAT_CHOICES = [
    "counterspell",
    "eschew_materials",
    "familiar",
    "hand_of_the_apprentice",
    "reach_spell",
    "widen_spell",
]
WIZARD_METAMAGIC_FEAT_CHOICES = ["reach_spell", "widen_spell"]
WIZARD_BONDED_ITEM_CHOICES = ["wand", "ring", "staff", "weapon", "other_item"]

WIZARD_SCHOOL_INITIAL_SPELLS = {
    "abjuration": "feather_fall",
    "conjuration": "summon_animal",
    "divination": "true_strike",
    "enchantment": "charm",
    "evocation": "shocking_grasp",
    "illusion": "illusory_object",
    "necromancy": "grim_tendrils",
    "transmutation": "magic_weapon",
}
WIZARD_SCHOOL_FOCUS_SPELLS = {
    "abjuration": "protective_ward",
    "conjuration": "augment_summoning",
    "divination": "diviners_sight",
    "enchantment": "charming_words",
    "evocation": "force_bolt",
    "illusion": "warped_terrain",
    "necromancy": "call_of_the_grave",
    "transmutation": "physical_boost",
}

# Table 3-19: Wizard spells per day.
WIZARD_SPELLS_PER_DAY = {
    1: {"cantrip": 5, "rank_1": 2},
    2: {"cantrip": 5, "rank_1": 3},
    3: {"cantrip": 5, "rank_1": 3, "rank_2": 2},
    4: {"cantrip": 5, "rank_1": 3, "rank_2": 3},
    5: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 2},
    6: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3},
    7: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 2},
    8: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3},
    9: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 2},
    10: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3},
    11: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 2},
    12: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3},
    13: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3, "rank_7": 2},
    14: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3, "rank_7": 3},
    15: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3, "rank_7": 3, "rank_8": 2},
    16: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3, "rank_7": 3, "rank_8": 3},
    17: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3, "rank_7": 3, "rank_8": 3, "rank_9": 2},
    18: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3, "rank_7": 3, "rank_8": 3, "rank_9": 3},
    19: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3, "rank_7": 3, "rank_8": 3, "rank_9": 3, "rank_10": 1},
    20: {"cantrip": 5, "rank_1": 3, "rank_2": 3, "rank_3": 3, "rank_4": 3, "rank_5": 3, "rank_6": 3, "rank_7": 3, "rank_8": 3, "rank_9": 3, "rank_10": 1},
}

WIZARD_PROMPT = (
    "KEY ABILITY: INTELLIGENCE\n"
    "At 1st level, your class gives you an ability boost to Intelligence.\n"
    "HIT POINTS: 6 plus your Constitution Modifier\n\n"
    "INITIAL PROFICIENCIES (summary):\n"
    "Perception: Trained\n"
    "Saving Throws: Trained Fortitude, Trained Reflex, Expert Will\n"
    "Attacks: Trained simple weapons + unarmed\n"
    "Defenses: Trained unarmored defense\n\n"
    "CLASS FEATURES:\n"
    "Arcane Spellcasting (prepared, spellbook-based)\n"
    "Arcane Bond (Drain Bonded Item)\n"
    "Arcane Thesis\n"
    "Arcane School specialization OR Universalist\n"
    "During setup choose school/universalist, thesis, bonded focus, and 1st-level class feat.\n"
    "Daily preparations wykonujesz na początku scenariusza.\n"
    "Spell Blending: modyfikuje budżet slotów/cantripów podczas tych przygotowań.\n"
    "Spell Substitution: osobna akcja poza walką (10 minut), limit 1 raz na scenariusz."
)


def WizardStatus() -> Status:
    return Status(
        id="wizard",
        label="Wizard",
        data={
            "ui_prompt": WIZARD_PROMPT,
            "class_hp": 6,
            "ui_choice_kind": "wizard_setup",
            "wizard_key_ability_choices": list(WIZARD_KEY_ABILITY_CHOICES),
            "wizard_arcane_study_choices": list(WIZARD_ARCANE_STUDY_CHOICES),
            "wizard_arcane_school_choices": list(WIZARD_ARCANE_SCHOOL_CHOICES),
            "wizard_arcane_thesis_choices": list(WIZARD_ARCANE_THESIS_CHOICES),
            "wizard_feat_choices": list(WIZARD_FEAT_CHOICES),
            "wizard_metamagic_feat_choices": list(WIZARD_METAMAGIC_FEAT_CHOICES),
            "wizard_bonded_item_choices": list(WIZARD_BONDED_ITEM_CHOICES),
            "wizard_school_initial_spells": dict(WIZARD_SCHOOL_INITIAL_SPELLS),
            "wizard_school_focus_spells": dict(WIZARD_SCHOOL_FOCUS_SPELLS),
            "wizard_spells_per_day": {level: dict(slots) for level, slots in WIZARD_SPELLS_PER_DAY.items()},
            "wizard_spellbook_start_cantrips": 10,
            "wizard_spellbook_start_rank1_spells": 5,
            "wizard_spellbook_auto_add_spells_per_level": 2,
            "wizard_prepared_cantrips_per_day": 5,
            "wizard_prepared_rank1_spells_per_day": 2,
            "wizard_specialist_bonus_cantrip": 1,
            "wizard_specialist_bonus_slot_per_rank": True,
            "wizard_universalist_bonus_feat": True,
            "set_actor_attrs": {"class_name": "wizard"},
        },
    )


WIZARD_STATUS = WizardStatus()

__all__ = [
    "WIZARD_KEY_ABILITY_CHOICES",
    "WIZARD_ARCANE_SCHOOL_CHOICES",
    "WIZARD_ARCANE_STUDY_CHOICES",
    "WIZARD_ARCANE_THESIS_CHOICES",
    "WIZARD_FEAT_CHOICES",
    "WIZARD_METAMAGIC_FEAT_CHOICES",
    "WIZARD_BONDED_ITEM_CHOICES",
    "WIZARD_SCHOOL_INITIAL_SPELLS",
    "WIZARD_SCHOOL_FOCUS_SPELLS",
    "WIZARD_SPELLS_PER_DAY",
    "WIZARD_PROMPT",
    "WizardStatus",
    "WIZARD_STATUS",
]
