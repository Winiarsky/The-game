from __future__ import annotations

from statuses.base import Status

ELVEN_LORE_DESCRIPTION = (
    "Stajesz się trained w Arcana i Nature.\n"
    "Jeśli już jesteś trained w jednej z nich, wybierasz inny skill.\n"
    "Dodatkowo stajesz się trained w Elven Lore."
)


def ElvenLoreStatus() -> Status:
    """Feat: Elven Lore."""
    return Status(
        id="elven_lore",
        label="Elven Lore",
        data={
            "ui_description": ELVEN_LORE_DESCRIPTION,
            "ui_choice_kind": "elven_lore",
            "trained_skills": ["arcana", "nature"],
            "trained_lore": ["elven_lore"],
            "elven_lore_replacements": [],
            "elven_lore_replacement_choices": [
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


ELVEN_LORE_STATUS = ElvenLoreStatus()

__all__ = ["ElvenLoreStatus", "ELVEN_LORE_STATUS", "ELVEN_LORE_DESCRIPTION"]
