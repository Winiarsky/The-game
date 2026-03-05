from __future__ import annotations

from statuses.base import Status

GNOME_OBSESSION_DESCRIPTION = (
    "Wybierz 1 Lore skill. Zyskujesz w nim trained.\n"
    "Na 2 poziomie: expert, na 7: master, na 15: legendary "
    "(dotyczy też Lore z backgroundu).\n"
    "W tym silniku zapisujemy wybór Lore i tabelę progresji."
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
