from __future__ import annotations

from statuses.base import Status

VERY_SNEAKY_DESCRIPTION = (
    "Podczas Stealth poruszasz się z normalną prędkością zamiast połowy. (Opisowo)"
)


def VerySneakyStatus() -> Status:
    """Feat: Very Sneaky (opis do UI)."""
    return Status(
        id="very_sneaky",
        label="Very Sneaky",
        data={"ui_description": VERY_SNEAKY_DESCRIPTION},
    )


VERY_SNEAKY_STATUS = VerySneakyStatus()

__all__ = ["VerySneakyStatus", "VERY_SNEAKY_STATUS", "VERY_SNEAKY_DESCRIPTION"]
