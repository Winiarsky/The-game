from __future__ import annotations

from statuses.base import Status

ELVEN_WEAPON_FAMILIARITY_DESCRIPTION = (
    "otrzymujesz bieglosc w poslugiwaniu sie dlugimi lukami, kuszami, "
    "dlugim mieczem oraz rapierem"
)


def ElvenWeaponFamiliarityStatus() -> Status:
    """Feat: Elven Weapon Familiarity (opis do UI)."""
    return Status(
        id="elven_weapon_familiarity",
        label="Elven Weapon Familiarity",
        data={"ui_description": ELVEN_WEAPON_FAMILIARITY_DESCRIPTION},
    )


ELVEN_WEAPON_FAMILIARITY_STATUS = ElvenWeaponFamiliarityStatus()

__all__ = [
    "ElvenWeaponFamiliarityStatus",
    "ELVEN_WEAPON_FAMILIARITY_STATUS",
    "ELVEN_WEAPON_FAMILIARITY_DESCRIPTION",
]
