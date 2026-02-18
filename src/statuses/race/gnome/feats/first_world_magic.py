from __future__ import annotations

from statuses.base import Status

FIRST_WORLD_MAGIC_DESCRIPTION = (
    "wybierz sztuczke z dziedziny primal, mozesz jej swobodnie uzywac"
)


def FirstWorldMagicStatus() -> Status:
    """Feat: First World Magic (opis do UI)."""
    return Status(
        id="first_world_magic",
        label="First World Magic",
        data={"ui_description": FIRST_WORLD_MAGIC_DESCRIPTION},
    )


FIRST_WORLD_MAGIC_STATUS = FirstWorldMagicStatus()

__all__ = [
    "FirstWorldMagicStatus",
    "FIRST_WORLD_MAGIC_STATUS",
    "FIRST_WORLD_MAGIC_DESCRIPTION",
]
