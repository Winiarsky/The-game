from __future__ import annotations

from statuses.base import Status
from statuses.familiar import FAMILIAR_OWNER_STATUS

FAMILIAR_DESCRIPTION = (
    "Familiar: zyskujesz familiara i mozesz korzystac z akcji Command Familiar."
)


def FamiliarStatus() -> Status:
    return Status(
        id="familiar",
        label="Familiar",
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
