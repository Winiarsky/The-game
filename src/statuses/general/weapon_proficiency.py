from __future__ import annotations

from statuses.base import Status

WEAPON_PROFICIENCY_DESCRIPTION = (
    "Bieglosc w prostych broniach, potem w wojennych, potem w wybranej zaawansowanej. "
    "Mozna brac wielokrotnie (progresja). Na razie licz recznie."
)


def WeaponProficiencyStatus() -> Status:
    """Feat: Weapon Proficiency (opis do UI)."""
    return Status(
        id="weapon_proficiency",
        label="Weapon Proficiency",
        data={"ui_description": WEAPON_PROFICIENCY_DESCRIPTION},
    )


WEAPON_PROFICIENCY_STATUS = WeaponProficiencyStatus()

__all__ = [
    "WeaponProficiencyStatus",
    "WEAPON_PROFICIENCY_STATUS",
    "WEAPON_PROFICIENCY_DESCRIPTION",
]
