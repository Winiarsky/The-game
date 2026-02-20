from __future__ import annotations

from statuses.base import Status

TOUGHNESS_DESCRIPTION = (
    "Zwiekszasz max HP o swoj poziom i zmniejszasz DC recovery o 1. "
    "Na razie licz recznie."
)


def ToughnessStatus() -> Status:
    """Feat: Toughness (opis do UI)."""
    return Status(
        id="toughness",
        label="Toughness",
        data={"ui_description": TOUGHNESS_DESCRIPTION},
    )


TOUGHNESS_STATUS = ToughnessStatus()

__all__ = ["ToughnessStatus", "TOUGHNESS_STATUS", "TOUGHNESS_DESCRIPTION"]
