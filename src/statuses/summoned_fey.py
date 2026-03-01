from __future__ import annotations

from .base import Status


def SummonedFeyStatus(*, duration: int | None = 1, source: str | None = None) -> Status:
    return Status(
        id="summoned_fey",
        label="Summoned Fey",
        duration=duration,
        source=source,
        data={"effect_tags": ["summon", "fey"]},
    )

