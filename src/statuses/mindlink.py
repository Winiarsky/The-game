from __future__ import annotations

from .base import Status


def MindlinkStatus(
    *,
    source_id: str | None,
    source_turns_left: int | None = 3,
    duration: int | None = 3,
    source: str | None = None,
) -> Status:
    return Status(
        id="mindlink",
        label="Mindlink",
        duration=duration,
        source=source,
        data={
            "source_id": source_id,
            "source_turns_left": source_turns_left,
            "effect_tags": ["divination", "mental"],
        },
    )

