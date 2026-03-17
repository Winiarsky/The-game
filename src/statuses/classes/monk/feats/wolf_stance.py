from __future__ import annotations

from statuses.base import Status

WOLF_STANCE_DESCRIPTION = (
    "Wolf Stance: atakujesz profilem Wolf Jaw (1k8 P, agile, backstabber, finesse). "
    "Trip przy flankowaniu jest ograniczony do obecnego runtime akcji Trip."
)


def WolfStanceStatus() -> Status:
    return Status(
        id="wolf_stance",
        label="Wolf Stance",
        data={
            "ui_description": WOLF_STANCE_DESCRIPTION,
            "ui_prompt": WOLF_STANCE_DESCRIPTION,
        },
    )


WOLF_STANCE_STATUS = WolfStanceStatus()

__all__ = ["WolfStanceStatus", "WOLF_STANCE_STATUS", "WOLF_STANCE_DESCRIPTION"]
