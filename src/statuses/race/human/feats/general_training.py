from __future__ import annotations

from statuses.base import Status

GENERAL_TRAINING_DESCRIPTION = (
    "Zyskujesz 1. poziomowy general feat (UI placeholder do wyboru)."
)

GENERAL_TRAINING_CHOICES = [
    "toughness",
    "fleet",
    "diehard",
    "incredible_initiative",
    "breath_control",
    "canny_acumen",
    "dubious_knowledge",
    "recognize_spell",
    "trick_magic_item",
    "shield_block",
    "assurance",
    "skill_training",
    "weapon_proficiency",
    "armor_proficiency",
    "adopted_ancestry",
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
