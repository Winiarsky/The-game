from __future__ import annotations

from statuses.base import Status

NATURAL_AMBITION_DESCRIPTION = (
    "Zyskujesz 1. poziomowy class feat (UI placeholder)."
)

NATURAL_AMBITION_CLASS_FEAT_CHOICES = {
    "alchemist": [
        "quick_alchemy_allow",
        "quick_bomber",
        "far_lobber",
        "alchemical_savant",
        "alchemist_familiar_guidance",
        "advanced_alchemy",
    ],
    "barbarian": [
        "moment_of_clarity",
        "raging_thrower",
        "cute_vision",
    ],
    "bard": [
        "bardic_lore",
        "lingering_composition",
        "versatile_performance",
        "reach_spell",
    ],
    "champion": [
        "raise_shield_allow",
        "deific_weapon",
    ],
}


def NaturalAmbitionStatus() -> Status:
    """Feat: Natural Ambition (UI placeholder)."""
    return Status(
        id="natural_ambition",
        label="Natural Ambition",
        data={
            "ui_description": NATURAL_AMBITION_DESCRIPTION,
            "ui_choice_kind": "natural_ambition",
            "natural_ambition_class_feat_choices": {
                key: list(values) for key, values in NATURAL_AMBITION_CLASS_FEAT_CHOICES.items()
            },
            "class_name": None,
            "class_feat": None,
        },
    )


NATURAL_AMBITION_STATUS = NaturalAmbitionStatus()

__all__ = [
    "NATURAL_AMBITION_DESCRIPTION",
    "NATURAL_AMBITION_CLASS_FEAT_CHOICES",
    "NaturalAmbitionStatus",
    "NATURAL_AMBITION_STATUS",
]
