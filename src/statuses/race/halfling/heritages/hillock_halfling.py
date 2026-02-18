from __future__ import annotations

from statuses.base import Status

HILLOCK_HALFLING_DESCRIPTION = (
    "Podczas odpoczynku nocnego odzyskujesz dodatkowo tyle HP, jaki masz poziom."
)


def HillockHalflingStatus() -> Status:
    """Heritage: Hillock Halfling (opisowo)."""
    return Status(
        id="hillock_halfling",
        label="Hillock Halfling",
        data={"ui_description": HILLOCK_HALFLING_DESCRIPTION},
    )


HILLOCK_HALFLING_STATUS = HillockHalflingStatus()

__all__ = ["HillockHalflingStatus", "HILLOCK_HALFLING_STATUS", "HILLOCK_HALFLING_DESCRIPTION"]
