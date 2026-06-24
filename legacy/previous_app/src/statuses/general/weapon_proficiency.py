from __future__ import annotations

from statuses.base import Status

WEAPON_PROFICIENCY_DESCRIPTION = (
    "Bieglosc w prostych broniach, potem w wojennych, potem w wybranej zaawansowanej. "
    "Mozna brac wielokrotnie (progresja). Silnik zapisuje krok progresji."
)


def WeaponProficiencyStatus() -> Status:
    """Feat: Weapon Proficiency."""
    return Status(
        id="weapon_proficiency",
        label="Weapon Proficiency",
        data={
            "ui_description": WEAPON_PROFICIENCY_DESCRIPTION,
            "ui_choice_kind": "weapon_proficiency",
            "weapon_proficiency_grant": None,
            "weapon_proficiency_ranks": {},
            "weapon_proficiency_advanced_choices": [
                "composite_longbow",
                "falcata",
                "falchion",
                "fire_poi",
                "flickmace",
                "katana",
                "meteor_hammer",
                "sawtooth_sabre",
            ],
        },
    )


WEAPON_PROFICIENCY_STATUS = WeaponProficiencyStatus()

__all__ = [
    "WeaponProficiencyStatus",
    "WEAPON_PROFICIENCY_STATUS",
    "WEAPON_PROFICIENCY_DESCRIPTION",
]
