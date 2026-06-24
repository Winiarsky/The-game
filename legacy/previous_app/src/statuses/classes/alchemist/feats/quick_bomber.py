from __future__ import annotations

from statuses.base import Status

QUICK_BOMBER_DESCRIPTION = (
    "Rzut bombą kosztuje o 1 akcję mniej (minimum 1)."
)


def QuickBomberStatus() -> Status:
    """Feat: Quick Bomber."""
    return Status(
        id="quick_bomber",
        label="Quick Bomber",
        data={
            "ui_description": QUICK_BOMBER_DESCRIPTION,
            "bomb_action_cost_reduction": 1,
        },
    )


QUICK_BOMBER_STATUS = QuickBomberStatus()

__all__ = [
    "QUICK_BOMBER_DESCRIPTION",
    "QuickBomberStatus",
    "QUICK_BOMBER_STATUS",
]
