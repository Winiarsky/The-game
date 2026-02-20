from __future__ import annotations

from statuses.base import Status

FLEET_DESCRIPTION = "Twoja predkosc zwieksza sie o 5 stop. Na razie opisowo."


def FleetStatus() -> Status:
    """Feat: Fleet (opis do UI)."""
    return Status(
        id="fleet",
        label="Fleet",
        data={"ui_description": FLEET_DESCRIPTION},
    )


FLEET_STATUS = FleetStatus()

__all__ = ["FleetStatus", "FLEET_STATUS", "FLEET_DESCRIPTION"]
