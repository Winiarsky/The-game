from __future__ import annotations

from statuses.base import Status

FEY_TOUCHED_GNOME_DESCRIPTION = (
    "wybierz sztuczke ze szkoly Arcana, mozesz jej uzywac w dowolnym momencie"
)


def FeyTouchedGnomeStatus() -> Status:
    """Heritage: Fey-touched Gnome."""
    return Status(
        id="fey_touched_gnome",
        label="Fey-touched Gnome",
        data={
            "ui_description": FEY_TOUCHED_GNOME_DESCRIPTION,
            "fey_touched_cantrip": None,
        },
    )


FEY_TOUCHED_GNOME_STATUS = FeyTouchedGnomeStatus()

__all__ = [
    "FeyTouchedGnomeStatus",
    "FEY_TOUCHED_GNOME_STATUS",
    "FEY_TOUCHED_GNOME_DESCRIPTION",
]
