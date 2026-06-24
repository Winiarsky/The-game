from __future__ import annotations

from .base import Status


def UnseenServantStatus(*, duration: int | None = 3, source: str | None = None) -> Status:
    return Status(
        id="unseen_servant",
        label="Unseen Servant",
        duration=duration,
        source=source,
        data={"ui_description": "Niewidzialny pomocnik wspiera drobne czynnosci (opisowo)."},
    )

