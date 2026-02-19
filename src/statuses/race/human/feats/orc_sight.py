from __future__ import annotations

from statuses.base import Status
from statuses.darkvision import DARKVISION_STATUS

ORC_SIGHT_DESCRIPTION = (
    "Wymaga low-light vision. Otrzymujesz darkvision (widzenie w ciemnosci), "
    "w ciemnosci widzisz tylko w odcieniach szarosci. "
    "Specjalne: tylko na 1. poziomie, bez retrainu."
)


def OrcSightStatus() -> Status:
    """Feat: Orc Sight."""
    return Status(
        id="orc_sight",
        label="Orc Sight",
        data={
            "ui_description": ORC_SIGHT_DESCRIPTION,
            "grants_statuses": [DARKVISION_STATUS],
        },
    )


ORC_SIGHT_STATUS = OrcSightStatus()

__all__ = ["OrcSightStatus", "ORC_SIGHT_STATUS", "ORC_SIGHT_DESCRIPTION"]
