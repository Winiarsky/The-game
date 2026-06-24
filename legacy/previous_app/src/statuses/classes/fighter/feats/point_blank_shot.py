from __future__ import annotations

from statuses.base import Status

POINT_BLANK_SHOT_DESCRIPTION = (
    "Point-Blank Shot (Open, Stance): ignorujesz karę volley; "
    "dla broni bez volley +2 circumstance do obrażeń w 1. przyroście zasięgu."
)


def PointBlankShotStatus() -> Status:
    return Status(
        id="point_blank_shot",
        label="Point-Blank Shot",
        data={"ui_description": POINT_BLANK_SHOT_DESCRIPTION, "ui_prompt": POINT_BLANK_SHOT_DESCRIPTION},
    )


POINT_BLANK_SHOT_STATUS = PointBlankShotStatus()

__all__ = ["PointBlankShotStatus", "POINT_BLANK_SHOT_STATUS", "POINT_BLANK_SHOT_DESCRIPTION"]
