from __future__ import annotations

from statuses.base import Status

ASSURANCE_DESCRIPTION = (
    "Wybierz skill w ktorym jestes trained: mozesz zamiast rzutu przyjac wynik 10 + "
    "twoj proficiency bonus (bez innych modyfikatorow). "
    "Mozna brac wiele razy (inny skill). Wybor skilla jest zapisywany na statusie."
)


def AssuranceStatus() -> Status:
    """Feat: Assurance."""
    return Status(
        id="assurance",
        label="Assurance",
        data={
            "ui_description": ASSURANCE_DESCRIPTION,
            "ui_choice_kind": "assurance",
            "assurance_skill_choices": [],
            "assurance_skill": None,
        },
    )


ASSURANCE_STATUS = AssuranceStatus()

__all__ = ["AssuranceStatus", "ASSURANCE_STATUS", "ASSURANCE_DESCRIPTION"]
