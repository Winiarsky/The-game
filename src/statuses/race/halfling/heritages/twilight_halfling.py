from __future__ import annotations

from statuses.base import Status
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

TWILIGHT_HALFLING_DESCRIPTION = "Zyskujesz low-light vision."


def TwilightHalflingStatus() -> Status:
    """Heritage: Twilight Halfling."""
    return Status(
        id="twilight_halfling",
        label="Twilight Halfling",
        data={
            "ui_description": TWILIGHT_HALFLING_DESCRIPTION,
            "grants_statuses": [DIM_LIGHT_VISION_STATUS],
        },
    )


TWILIGHT_HALFLING_STATUS = TwilightHalflingStatus()

__all__ = ["TwilightHalflingStatus", "TWILIGHT_HALFLING_STATUS", "TWILIGHT_HALFLING_DESCRIPTION"]
