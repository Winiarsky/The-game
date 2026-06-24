from __future__ import annotations

from statuses.base import Status
from statuses.familiar import FAMILIAR_OWNER_STATUS

FAMILIAR_DESCRIPTION = (
    "Chowaniec: zyskujesz chowanca i mozesz korzystac z akcji Komenderuj chowanca."
)


def FamiliarStatus() -> Status:
    return Status(
        id="familiar",
        label="Chowaniec",
        data={
            "ui_description": FAMILIAR_DESCRIPTION,
            "ui_prompt": FAMILIAR_DESCRIPTION,
            "grants_statuses": [FAMILIAR_OWNER_STATUS],
        },
    )


FAMILIAR_STATUS = FamiliarStatus()

__all__ = [
    "FAMILIAR_DESCRIPTION",
    "FamiliarStatus",
    "FAMILIAR_STATUS",
]
