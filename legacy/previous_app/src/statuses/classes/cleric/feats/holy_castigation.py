from __future__ import annotations

from statuses.base import Status

HOLY_CASTIGATION_DESCRIPTION = (
    "Holy Castigation: Heal moze raniac fiendy tak jak undead. "
    "W tej implementacji alignment jest pomijany."
)


def HolyCastigationStatus() -> Status:
    return Status(
        id="holy_castigation",
        label="Holy Castigation",
        data={
            "ui_description": HOLY_CASTIGATION_DESCRIPTION,
            "ui_prompt": HOLY_CASTIGATION_DESCRIPTION,
        },
    )


HOLY_CASTIGATION_STATUS = HolyCastigationStatus()

__all__ = [
    "HOLY_CASTIGATION_DESCRIPTION",
    "HolyCastigationStatus",
    "HOLY_CASTIGATION_STATUS",
]
