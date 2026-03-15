from __future__ import annotations

from statuses.base import Status

ARMOR_PROFICIENCY_DESCRIPTION = (
    "Stajesz sie biegly w lekkich zbrojach; jesli juz jestes, w srednich; "
    "jesli w srednich, w ciezkich. Mozna brac wielokrotnie (progresja). "
    "Silnik zapisuje wybrany krok progresji na statusie."
)


def ArmorProficiencyStatus() -> Status:
    """Feat: Armor Proficiency."""
    return Status(
        id="armor_proficiency",
        label="Armor Proficiency",
        data={
            "ui_description": ARMOR_PROFICIENCY_DESCRIPTION,
            "ui_choice_kind": "armor_proficiency",
            "armor_proficiency_grant": None,
            "defense_proficiency_ranks": {},
        },
    )


ARMOR_PROFICIENCY_STATUS = ArmorProficiencyStatus()

__all__ = [
    "ArmorProficiencyStatus",
    "ARMOR_PROFICIENCY_STATUS",
    "ARMOR_PROFICIENCY_DESCRIPTION",
]
