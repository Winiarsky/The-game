from __future__ import annotations

from .base import Status


def VentriloquismStatus(*, duration: int | None = 1, source: str | None = None) -> Status:
    return Status(
        id="ventriloquism",
        label="Ventriloquism",
        duration=duration,
        source=source,
        data={"effect_tags": ["illusion", "auditory"]},
    )

