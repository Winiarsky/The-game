from __future__ import annotations

from statuses.base import Status

GNOME_OBSESSION_DESCRIPTION = (
    "Masz obsesyjna, gleboka fascynacje jedna dziedzina wiedzy.\n"
    "Kiedy: po wybraniu featu wskazujesz 1 Lore skill.\n"
    "Efekt: dostajesz trained w wybranym Lore oraz zapis progresji tej samej "
    "specjalizacji: 2 poziom -> expert, 7 -> master, 15 -> legendary "
    "(mapowane przez gnome_obsession_progression)."
)


def GnomeObsessionStatus() -> Status:
    """Feat: Gnome Obsession (opis do UI)."""
    return Status(
        id="gnome_obsession",
        label="Gnome Obsession",
        data={
            "ui_description": GNOME_OBSESSION_DESCRIPTION,
            "ui_choice_kind": "gnome_obsession",
            "gnome_obsession_lore": None,
            "trained_lore": [],
            "gnome_obsession_progression": {
                "2": "expert",
                "7": "master",
                "15": "legendary",
            },
        },
    )


GNOME_OBSESSION_STATUS = GnomeObsessionStatus()

__all__ = [
    "GnomeObsessionStatus",
    "GNOME_OBSESSION_STATUS",
    "GNOME_OBSESSION_DESCRIPTION",
]
