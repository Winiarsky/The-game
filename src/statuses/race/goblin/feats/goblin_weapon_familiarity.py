from __future__ import annotations

from statuses.base import Status

GOBLIN_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Jesteś biegły z dogslicer i horsechopper. Masz dostęp do broni goblińskich. (Opisowo)"
)


def GoblinWeaponFamiliarityStatus() -> Status:
    """Feat: Goblin Weapon Familiarity (opis do UI)."""
    return Status(
        id="goblin_weapon_familiarity",
        label="Goblin Weapon Familiarity",
        data={"ui_description": GOBLIN_WEAPON_FAMILIARITY_DESCRIPTION},
    )


GOBLIN_WEAPON_FAMILIARITY_STATUS = GoblinWeaponFamiliarityStatus()

__all__ = [
    "GoblinWeaponFamiliarityStatus",
    "GOBLIN_WEAPON_FAMILIARITY_STATUS",
    "GOBLIN_WEAPON_FAMILIARITY_DESCRIPTION",
]
