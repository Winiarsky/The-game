from __future__ import annotations

from statuses.base import Status

UNCONVENTIONAL_WEAPONRY_DESCRIPTION = (
    "Masz dostęp do wybranej broni z innej kultury; traktujesz ją jako prostą. (UI only)"
)


def UnconventionalWeaponryStatus() -> Status:
    """Feat: Unconventional Weaponry (UI only)."""
    return Status(
        id="unconventional_weaponry",
        label="Unconventional Weaponry",
        data={
            "ui_description": UNCONVENTIONAL_WEAPONRY_DESCRIPTION,
            "weapon_name": None,
            "counts_as": "simple",
        },
    )


UNCONVENTIONAL_WEAPONRY_STATUS = UnconventionalWeaponryStatus()

__all__ = [
    "UnconventionalWeaponryStatus",
    "UNCONVENTIONAL_WEAPONRY_STATUS",
    "UNCONVENTIONAL_WEAPONRY_DESCRIPTION",
]
