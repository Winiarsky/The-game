from __future__ import annotations

from statuses.base import Status

CHAMELEON_GNOME_DESCRIPTION = (
    "Na początku scenariusza wybierz teren; "
    "otrzymujesz +2 circumstance do Stealth na wybranym terenie."
)


def ChameleonGnomeStatus() -> Status:
    """Heritage: Chameleon Gnome."""
    return Status(
        id="chameleon_gnome",
        label="Chameleon Gnome",
        data={
            "ui_description": CHAMELEON_GNOME_DESCRIPTION,
            "chameleon_terrain": None,
        },
    )


CHAMELEON_GNOME_STATUS = ChameleonGnomeStatus()

__all__ = ["ChameleonGnomeStatus", "CHAMELEON_GNOME_STATUS", "CHAMELEON_GNOME_DESCRIPTION"]
