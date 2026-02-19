from __future__ import annotations

from statuses.base import Status

SKILLED_HERITAGE_DESCRIPTION = (
    "Your ingenuity allows you to train in a wide variety of skills.\n"
    "You become trained in one skill of your choice.\n"
    "At 5th level, you become an expert in the chosen skill."
)


def SkilledHeritageStatus() -> Status:
    """Heritage: Skilled Heritage (prompt only)."""
    return Status(
        id="skilled_heritage",
        label="Skilled Heritage",
        data={"ui_description": SKILLED_HERITAGE_DESCRIPTION},
    )


SKILLED_HERITAGE_STATUS = SkilledHeritageStatus()

__all__ = ["SkilledHeritageStatus", "SKILLED_HERITAGE_STATUS", "SKILLED_HERITAGE_DESCRIPTION"]
