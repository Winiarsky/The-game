from __future__ import annotations

from statuses.base import Status

HALFLING_LORE_DESCRIPTION = (
    "Fluff: Halfling Lore zbiera typowe dla niziolkow sztuczki, opowiesci i codzienne umiejetnosci przydatne w drodze.\n"
    "Mechanika:\n"
    "- Kiedy: Po wybraniu tej opcji.\n"
    "- Efekt:\n"
    "  - Stajesz sie trained w Acrobatics i Stealth.\n"
    "  - Dodatkowo stajesz sie trained w Halfling Lore.\n"
    "  - Jesli juz masz training w Acrobatics albo Stealth, wybierasz inny skill jako zamiennik.\n"
    "  - Przykład: jesli masz juz Acrobatics z backgroundu, feat zostawi ci Stealth i pozwoli dobrac np. Arcana."
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
