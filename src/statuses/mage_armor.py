from __future__ import annotations

from .base import Status


def MageArmorStatus(*, duration: int | None = 10, source: str | None = None) -> Status:
    return Status(
        id="mage_armor",
        label="Mage Armor",
        duration=duration,
        source=source,
        data={"effect_tags": ["abjuration", "defense"]},
    )

