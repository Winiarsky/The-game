from __future__ import annotations

from statuses.base import Status

HALFLING_WEAPON_FAMILIARITY_DESCRIPTION = (
    "Jesteś biegły ze sling, halfling sling staff i shortsword. "
    "Masz dostęp do broni halflingów. (Opisowo)"
)


def HalflingWeaponFamiliarityStatus() -> Status:
    """Feat: Halfling Weapon Familiarity (opis do UI)."""
    return Status(
        id="halfling_weapon_familiarity",
        label="Halfling Weapon Familiarity",
        data={"ui_description": HALFLING_WEAPON_FAMILIARITY_DESCRIPTION},
    )


HALFLING_WEAPON_FAMILIARITY_STATUS = HalflingWeaponFamiliarityStatus()

__all__ = [
    "HalflingWeaponFamiliarityStatus",
    "HALFLING_WEAPON_FAMILIARITY_STATUS",
    "HALFLING_WEAPON_FAMILIARITY_DESCRIPTION",
]
