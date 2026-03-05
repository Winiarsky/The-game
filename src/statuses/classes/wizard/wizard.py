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
    1: {"cantrips": 5, "1st": 2},
    2: {"cantrips": 5, "1st": 3},
    3: {"cantrips": 5, "1st": 3, "2nd": 2},
    4: {"cantrips": 5, "1st": 3, "2nd": 3},
    5: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 2},
    6: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3},
    7: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 2},
    8: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3},
    9: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 2},
    10: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3},
    11: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 2},
    12: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 3},
    13: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 3, "7th": 2},
    14: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 3, "7th": 3},
    15: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 3, "7th": 3, "8th": 2},
    16: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 3, "7th": 3, "8th": 3},
    17: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 3, "7th": 3, "8th": 3, "9th": 2},
    18: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 3, "7th": 3, "8th": 3, "9th": 3},
    19: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 3, "7th": 3, "8th": 3, "9th": 3, "10th": 1},
    20: {"cantrips": 5, "1st": 3, "2nd": 3, "3rd": 3, "4th": 3, "5th": 3, "6th": 3, "7th": 3, "8th": 3, "9th": 3, "10th": 1},
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
    "Spell Blending / Spell Substitution: v1 tracked as manual reminders in prompts."
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
