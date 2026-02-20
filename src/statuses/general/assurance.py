from __future__ import annotations

from statuses.base import Status

ASSURANCE_DESCRIPTION = (
    "Wybierz skill w ktorym jestes trained: mozesz zamiast rzutu przyjac wynik 10 + "
    "twoj proficiency bonus (bez innych modyfikatorow). "
    "Mozna brac wiele razy (inny skill). Na razie recznie."
)


def AssuranceStatus() -> Status:
    """Feat: Assurance (opis do UI)."""
    return Status(
        id="assurance",
        label="Assurance",
        data={"ui_description": ASSURANCE_DESCRIPTION},
    )


ASSURANCE_STATUS = AssuranceStatus()

__all__ = ["AssuranceStatus", "ASSURANCE_STATUS", "ASSURANCE_DESCRIPTION"]
