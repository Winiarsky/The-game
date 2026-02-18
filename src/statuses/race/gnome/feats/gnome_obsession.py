from __future__ import annotations

from statuses.base import Status

GNOME_OBSESSION_DESCRIPTION = (
    "otrzymujesz trained w skilu Lore, na 2 poziomie trained zmienia sie w "
    "expert, na 7 w master a na 15 w legendary"
)


def GnomeObsessionStatus() -> Status:
    """Feat: Gnome Obsession (opis do UI)."""
    return Status(
        id="gnome_obsession",
        label="Gnome Obsession",
        data={"ui_description": GNOME_OBSESSION_DESCRIPTION},
    )


GNOME_OBSESSION_STATUS = GnomeObsessionStatus()

__all__ = [
    "GnomeObsessionStatus",
    "GNOME_OBSESSION_STATUS",
    "GNOME_OBSESSION_DESCRIPTION",
]
