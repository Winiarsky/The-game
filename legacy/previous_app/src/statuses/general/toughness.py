from __future__ import annotations

from statuses.base import Status

TOUGHNESS_DESCRIPTION = (
    "Zwiekszasz max HP o swoj poziom oraz zmniejszasz DC recovery o 1 "
    "(oba elementy sa wspierane mechanicznie)."
)


def ToughnessStatus() -> Status:
    """Feat: Toughness."""
    return Status(
        id="toughness",
        label="Toughness",
        data={
            "ui_description": TOUGHNESS_DESCRIPTION,
            "max_hp_per_level": 1,
        },
    )


TOUGHNESS_STATUS = ToughnessStatus()

__all__ = ["ToughnessStatus", "TOUGHNESS_STATUS", "TOUGHNESS_DESCRIPTION"]
