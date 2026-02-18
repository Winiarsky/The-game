from __future__ import annotations

from statuses.base import Status

GNOME_WEAPON_FAMILIARITY_DESCRIPTION = "otrzymujesz bieglos w broni glaive i kukri"


def GnomeWeaponFamiliarityStatus() -> Status:
    """Feat: Gnome Weapon Familiarity (opis do UI)."""
    return Status(
        id="gnome_weapon_familiarity",
        label="Gnome Weapon Familiarity",
        data={"ui_description": GNOME_WEAPON_FAMILIARITY_DESCRIPTION},
    )


GNOME_WEAPON_FAMILIARITY_STATUS = GnomeWeaponFamiliarityStatus()

__all__ = [
    "GnomeWeaponFamiliarityStatus",
    "GNOME_WEAPON_FAMILIARITY_STATUS",
    "GNOME_WEAPON_FAMILIARITY_DESCRIPTION",
]
