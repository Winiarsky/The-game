from __future__ import annotations

from .base import Status


def TrueStrikeStatus(*, duration: int | None = 1, source: str | None = None) -> Status:
    return Status(
        id="true_strike",
        label="True Strike",
        duration=duration,
        source=source,
        data={"effect_tags": ["fortune", "divination"]},
    )

