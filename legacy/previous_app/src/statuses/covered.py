from __future__ import annotations

from statuses.base import Status


def CoveredStatus() -> Status:
    """Status osłony nadawany przez akcję Take Cover."""

    return Status(id="covered", label="Osłona")


COVERED_STATUS = CoveredStatus()
