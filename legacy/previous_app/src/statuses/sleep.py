from __future__ import annotations

from .base import Status


def SleepStatus(
    *,
    source_id: str | None,
    source_turns_left: int | None = 2,
    duration: int | None = 1,
    source: str | None = None,
) -> Status:
    return Status(
        id="sleep",
        label="Asleep",
        duration=duration,
        source=source,
        data={
            "source_id": source_id,
            "source_turns_left": source_turns_left,
            "effect_tags": ["sleep", "mental"],
        },
    )

