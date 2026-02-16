from __future__ import annotations

from statuses.base import Status

DWARVEN_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Otrzymujesz bieglosc w broniach: battle axe, pick, and warhammer"
)


def DwarvenWeaponFamiliarityStatus() -> Status:
    """Feat: Dwarven Weapon Familiarity (opis do UI)."""
    return Status(
        id="dwarven_weapon_familiarity",
        label="Dwarven Weapon Familiarity",
        data={"ui_description": DWARVEN_WEAPON_FAMILIARITY_DESCRIPTION},
    )


DWARVEN_WEAPON_FAMILIARITY_STATUS = DwarvenWeaponFamiliarityStatus()

__all__ = [
    "DwarvenWeaponFamiliarityStatus",
    "DWARVEN_WEAPON_FAMILIARITY_STATUS",
    "DWARVEN_WEAPON_FAMILIARITY_DESCRIPTION",
]
