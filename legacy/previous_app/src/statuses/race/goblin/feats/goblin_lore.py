from __future__ import annotations

from statuses.base import Status

GOBLIN_LORE_DESCRIPTION = (
    "Stajesz się trained w Nature i Stealth.\n"
    "Jeśli już jesteś trained w jednym z tych skilli, wybierasz inny skill.\n"
    "Dodatkowo stajesz się trained w Goblin Lore."
)


def GoblinLoreStatus() -> Status:
    """Feat: Goblin Lore (opis do UI)."""
    return Status(
        id="goblin_lore",
        label="Goblin Lore",
        data={
            "ui_description": GOBLIN_LORE_DESCRIPTION,
            "ui_choice_kind": "goblin_lore",
            "trained_skills": ["nature", "stealth"],
            "trained_lore": ["goblin_lore"],
            "goblin_lore_replacements": [],
            "goblin_lore_replacement_choices": [
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


GOBLIN_LORE_STATUS = GoblinLoreStatus()

__all__ = ["GoblinLoreStatus", "GOBLIN_LORE_STATUS", "GOBLIN_LORE_DESCRIPTION"]
