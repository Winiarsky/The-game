from __future__ import annotations

from statuses.base import Status
from statuses.familiar import FAMILIAR_OWNER_STATUS

LESHY_FAMILIAR_DESCRIPTION = (
    "Leshy Familiar: zyskujesz leshy familiar (uzywa ogolnej mechaniki familiar)."
)


def LeshyFamiliarStatus() -> Status:
    return Status(
        id="leshy_familiar",
        label="Leshy Familiar",
        data={
            "ui_description": LESHY_FAMILIAR_DESCRIPTION,
            "ui_prompt": LESHY_FAMILIAR_DESCRIPTION,
            "requires_druid_order": "leaf",
            "grants_statuses": [FAMILIAR_OWNER_STATUS],
        },
    )


LESHY_FAMILIAR_STATUS = LeshyFamiliarStatus()

__all__ = [
    "LESHY_FAMILIAR_DESCRIPTION",
    "LeshyFamiliarStatus",
    "LESHY_FAMILIAR_STATUS",
]
