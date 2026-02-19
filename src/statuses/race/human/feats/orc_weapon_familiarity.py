from __future__ import annotations

from statuses.base import Status

ORC_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Jestes biegly z falchion i greataxe. "
    "Masz dostep do broni orkow (opisowo)."
)


def OrcWeaponFamiliarityStatus() -> Status:
    """Feat: Orc Weapon Familiarity (opis do UI)."""
    return Status(
        id="orc_weapon_familiarity",
        label="Orc Weapon Familiarity",
        data={"ui_description": ORC_WEAPON_FAMILIARITY_DESCRIPTION},
    )


ORC_WEAPON_FAMILIARITY_STATUS = OrcWeaponFamiliarityStatus()

__all__ = [
    "OrcWeaponFamiliarityStatus",
    "ORC_WEAPON_FAMILIARITY_STATUS",
    "ORC_WEAPON_FAMILIARITY_DESCRIPTION",
]
