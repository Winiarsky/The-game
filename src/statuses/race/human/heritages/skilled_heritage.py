from __future__ import annotations

from statuses.base import Status

SKILLED_HERITAGE_DESCRIPTION = (
    "Twoja pomyslowosc pozwala ci opanowac wiele roznych umiejetnosci.\n"
    "Stajesz sie trained w jednym wybranym skillu.\n"
    "Na 5. poziomie awansujesz w tym skillu do expert."
)


def SkilledHeritageStatus() -> Status:
    """Heritage: Skilled Heritage."""
    return Status(
        id="skilled_heritage",
        label="Skilled Heritage",
        data={
            "ui_description": SKILLED_HERITAGE_DESCRIPTION,
            "ui_choice_kind": "skilled_heritage",
            "skilled_heritage_skill": None,
            "trained_skills": [],
            "skilled_heritage_progression": {"5": "expert"},
        },
    )


SKILLED_HERITAGE_STATUS = SkilledHeritageStatus()

__all__ = ["SkilledHeritageStatus", "SKILLED_HERITAGE_STATUS", "SKILLED_HERITAGE_DESCRIPTION"]
