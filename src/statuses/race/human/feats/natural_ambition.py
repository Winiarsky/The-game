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
    "cleric": [
        "deadly_simplicity",
        "domain_initiate",
        "harming_hands",
        "healing_hands",
        "holy_castigation",
        "reach_spell",
    ],
    "druid": [
        "animal_companion",
        "leshy_familiar",
        "reach_spell",
        "storm_born",
        "widen_spell",
        "wild_shape",
    ],
    "fighter": [
        "double_slice",
        "exacting_strike",
        "point_blank_shot",
        "power_attack",
        "reactive_shield",
        "snagging_strike",
        "sudden_charge",
    ],
    "monk": [
        "crane_stance",
        "dragon_stance",
        "ki_rush",
        "ki_strike",
        "monastic_weaponry",
        "mountain_stance",
        "tiger_stance",
        "wolf_stance",
    ],
    "ranger": [
        "animal_companion",
        "crossbow_ace",
        "hunted_shot",
        "monster_hunter",
        "twin_takedown",
    ],
    "sorcerer": [
        "counterspell",
        "dangerous_sorcery",
        "familiar",
        "reach_spell",
        "widen_spell",
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
