from __future__ import annotations

from .base import Status


def ImmobilizedStatus(*, duration: int | None = None, source: str | None = None, source_id: str | None = None, source_turns_left: int | None = None) -> Status:
    """Status blokujący akcje z tagiem move."""
    data = {
        "source_id": source_id,
        "source_turns_left": source_turns_left,
        "effect_tags": ["immobilized"],
    }
    return Status(
        id="immobilized",
        label="immobilized",
        duration=duration,
        source=source,
        data=data,
    )


IMMOBILIZED_STATUS = ImmobilizedStatus()
