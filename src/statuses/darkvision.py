from __future__ import annotations

from statuses.base import Status


def DarkVisionStatus() -> Status:
    """Status darkvision – blokuje efekty ciemności."""
    return Status(
        id="darkvision",
        label="Darkvision",
        data={"immune_status_tags": ["darkness"]},
    )


DARKVISION_STATUS = DarkVisionStatus()

__all__ = ["DarkVisionStatus", "DARKVISION_STATUS"]
