from __future__ import annotations

from statuses.base import Status

DIEHARD_DESCRIPTION = (
    "Umierasz dopiero na dying 5 zamiast dying 4 (wdrozone mechanicznie)."
)


def DiehardStatus() -> Status:
    """Feat: Diehard."""
    return Status(
        id="diehard",
        label="Diehard",
        data={"ui_description": DIEHARD_DESCRIPTION},
    )


DIEHARD_STATUS = DiehardStatus()

__all__ = ["DiehardStatus", "DIEHARD_STATUS", "DIEHARD_DESCRIPTION"]
