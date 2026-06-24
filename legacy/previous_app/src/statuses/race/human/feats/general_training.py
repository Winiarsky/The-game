from __future__ import annotations

from statuses.base import Status

GENERAL_TRAINING_DESCRIPTION = (
    "Zyskujesz 1. poziomowy general feat. Feat jest dodawany jako realny status."
)

GENERAL_TRAINING_CHOICES = [
    "additional_lore",
    "adopted_ancestry",
    "alchemical_crafting",
    "arcane_sense",
    "armor_proficiency",
    "assurance",
    "bargain_hunter",
    "battle_medicine",
    "breath_control",
    "canny_acumen",
    "cat_fall",
    "charming_liar",
    "combat_climber",
    "courtly_graces",
    "toughness",
    "fleet",
    "diehard",
    "incredible_initiative",
    "dubious_knowledge",
    "experienced_professional",
    "experienced_smuggler",
    "experienced_tracker",
    "fascinating_performance",
    "fast_recovery",
    "feather_step",
    "forager",
    "group_coercion",
    "group_impression",
    "hefty_hauler",
    "hobnobber",
    "impressive_performance",
    "intimidating_glare",
    "lengthy_diversion",
    "multilingual",
    "natural_medicine",
    "oddity_identification",
    "pickpocket",
    "quick_coercion",
    "quick_identification",
    "quick_jump",
    "quick_repair",
    "quick_squeeze",
    "read_lips",
    "recognize_spell",
    "ride",
    "trick_magic_item",
    "sign_language",
    "snare_crafting",
    "specialty_crafting",
    "subtle_theft",
    "survey_wildlife",
    "terrain_expertise",
    "terrain_stalker",
    "titan_wrestler",
    "train_animal",
    "underwater_marauder",
    "virtuosic_performer",
    "shield_block",
    "skill_training",
    "weapon_proficiency",
]


def GeneralTrainingStatus() -> Status:
    """Feat: General Training (UI placeholder)."""
    return Status(
        id="general_training",
        label="General Training",
        data={
            "ui_description": GENERAL_TRAINING_DESCRIPTION,
            "ui_choice_kind": "general_training",
            "general_feat_choices": list(GENERAL_TRAINING_CHOICES),
            "general_feat": None,
        },
    )


GENERAL_TRAINING_STATUS = GeneralTrainingStatus()

__all__ = [
    "GENERAL_TRAINING_DESCRIPTION",
    "GENERAL_TRAINING_CHOICES",
    "GeneralTrainingStatus",
    "GENERAL_TRAINING_STATUS",
]
