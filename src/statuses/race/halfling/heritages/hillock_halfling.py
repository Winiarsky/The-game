from __future__ import annotations

from statuses.base import Status

HILLOCK_HALFLING_DESCRIPTION = (
    "Przy nocnym odpoczynku odzyskujesz dodatkowo HP równe twojemu poziomowi.\n"
    "Gdy ktoś używa na tobie Treat Wounds, możesz zjeść przekąskę, aby dodać "
    "twój poziom do odzyskanych HP."
)


def HillockHalflingStatus() -> Status:
    """Heritage: Hillock Halfling."""
    return Status(
        id="hillock_halfling",
        label="Hillock Halfling",
        data={
            "ui_description": HILLOCK_HALFLING_DESCRIPTION,
            "overnight_healing_bonus_per_level": 1,
            "treat_wounds_healing_bonus_per_level": 1,
            "treat_wounds_requires_snack": True,
        },
    )


HILLOCK_HALFLING_STATUS = HillockHalflingStatus()

__all__ = ["HillockHalflingStatus", "HILLOCK_HALFLING_STATUS", "HILLOCK_HALFLING_DESCRIPTION"]
