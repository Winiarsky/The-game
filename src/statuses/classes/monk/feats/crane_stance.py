from __future__ import annotations

from statuses.base import Status

CRANE_STANCE_DESCRIPTION = (
    "Crane Stance: +1 circumstance AC; atakujesz profilem Crane Wing (1k6 B, agile, finesse). "
    "Leap ma zwiększony zasięg o 1 pole."
)


def CraneStanceStatus() -> Status:
    return Status(
        id="crane_stance",
        label="Crane Stance",
        data={
            "ui_description": CRANE_STANCE_DESCRIPTION,
            "ui_prompt": CRANE_STANCE_DESCRIPTION,
        },
    )


CRANE_STANCE_STATUS = CraneStanceStatus()

__all__ = ["CraneStanceStatus", "CRANE_STANCE_STATUS", "CRANE_STANCE_DESCRIPTION"]
