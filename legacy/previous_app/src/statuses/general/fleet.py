from __future__ import annotations

from statuses.base import Status

FLEET_DESCRIPTION = "Twoja bazowa predkosc zwieksza sie o 5 stop (wdrozone mechanicznie)."


def FleetStatus() -> Status:
    """Feat: Fleet."""
    return Status(
        id="fleet",
        label="Fleet",
        data={
            "ui_description": FLEET_DESCRIPTION,
            "base_speed_bonus_feet": 5,
        },
    )


FLEET_STATUS = FleetStatus()

__all__ = ["FleetStatus", "FLEET_STATUS", "FLEET_DESCRIPTION"]
