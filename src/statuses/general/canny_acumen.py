from __future__ import annotations

from statuses.base import Status

CANNY_ACUMEN_DESCRIPTION = (
    "Wybierz Fortitude/Reflex/Will lub Perception: stajesz sie ekspertem. "
    "Na 17 poziomie master. Na razie sledz recznie."
)


def CannyAcumenStatus() -> Status:
    """Feat: Canny Acumen (opis do UI)."""
    return Status(
        id="canny_acumen",
        label="Canny Acumen",
        data={"ui_description": CANNY_ACUMEN_DESCRIPTION},
    )


CANNY_ACUMEN_STATUS = CannyAcumenStatus()

__all__ = ["CannyAcumenStatus", "CANNY_ACUMEN_STATUS", "CANNY_ACUMEN_DESCRIPTION"]
