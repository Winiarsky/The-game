from __future__ import annotations

from statuses.base import Status

MONASTIC_WEAPONRY_DESCRIPTION = (
    "Monastic Weaponry: placeholder v1. "
    "Realna lista monk weapons i integracja z eventami jest zapisana do TODO."
)


def MonasticWeaponryStatus() -> Status:
    return Status(
        id="monastic_weaponry",
        label="Monastic Weaponry",
        data={
            "ui_description": MONASTIC_WEAPONRY_DESCRIPTION,
            "ui_prompt": MONASTIC_WEAPONRY_DESCRIPTION,
        },
    )


MONASTIC_WEAPONRY_STATUS = MonasticWeaponryStatus()

__all__ = ["MonasticWeaponryStatus", "MONASTIC_WEAPONRY_STATUS", "MONASTIC_WEAPONRY_DESCRIPTION"]
