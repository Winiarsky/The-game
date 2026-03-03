from __future__ import annotations

from statuses.base import Status

MOUNTAIN_STANCE_DESCRIPTION = (
    "Mountain Stance: +4 item AC, atakujesz profilem Falling Stone (1k8 B, forceful). "
    "Dex cap +0, speed -5 i shove/trip bonus: reminder (manual)."
)


def MountainStanceStatus() -> Status:
    return Status(
        id="mountain_stance",
        label="Mountain Stance",
        data={
            "ui_description": MOUNTAIN_STANCE_DESCRIPTION,
            "ui_prompt": MOUNTAIN_STANCE_DESCRIPTION,
        },
    )


MOUNTAIN_STANCE_STATUS = MountainStanceStatus()

__all__ = ["MountainStanceStatus", "MOUNTAIN_STANCE_STATUS", "MOUNTAIN_STANCE_DESCRIPTION"]
