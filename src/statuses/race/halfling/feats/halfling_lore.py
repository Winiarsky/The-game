from __future__ import annotations

from statuses.base import Status

HALFLING_LORE_DESCRIPTION = (
    "Stajesz się trained w Acrobatics i Stealth.\n"
    "Jeśli już jesteś trained w jednej z tych umiejętności, wybierasz inny skill.\n"
    "Dodatkowo stajesz się trained w Halfling Lore."
)


def HalflingLoreStatus() -> Status:
    """Feat: Halfling Lore."""
    return Status(
        id="halfling_lore",
        label="Halfling Lore",
        data={
            "ui_description": HALFLING_LORE_DESCRIPTION,
            "ui_choice_kind": "halfling_lore",
            "trained_skills": ["acrobatics", "stealth"],
            "trained_lore": ["halfling_lore"],
            "halfling_lore_replacements": [],
            "halfling_lore_replacement_choices": [
                "athletics",
                "acrobatics",
                "arcana",
                "crafting",
                "deception",
                "diplomacy",
                "intimidation",
                "medicine",
                "nature",
                "occultism",
                "performance",
                "religion",
                "society",
                "stealth",
                "survival",
                "thievery",
            ],
        },
    )


HALFLING_LORE_STATUS = HalflingLoreStatus()

__all__ = ["HalflingLoreStatus", "HALFLING_LORE_STATUS", "HALFLING_LORE_DESCRIPTION"]
