from __future__ import annotations

from .base import Status


def CharmedStatus(*, duration: int | None = 3, source: str | None = None) -> Status:
    return Status(
        id="charmed",
        label="Charmed",
        duration=duration,
        source=source,
        data={"effect_tags": ["charmed", "mental"]},
    )

