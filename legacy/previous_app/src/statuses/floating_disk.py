from __future__ import annotations

from .base import Status


def FloatingDiskStatus(*, duration: int | None = 10, source: str | None = None) -> Status:
    return Status(
        id="floating_disk",
        label="Floating Disk",
        duration=duration,
        source=source,
        data={"ui_description": "Dysk unosi ekwipunek i odciaza bohatera (uproszczenie)."},
    )

