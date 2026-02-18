from __future__ import annotations

from statuses.base import Status

HALFLING_LUCK_DESCRIPTION = (
    "Gdy nie zdasz testu umiejętności lub rzutu obronnego, możesz przerzucić. "
    "Musisz użyć nowego wyniku. Po użyciu efekt znika (na scenariusz)."
)


def HalflingLuckStatus() -> Status:
    """Feat: Halfling Luck."""
    return Status(
        id="halfling_luck",
        label="Halfling Luck",
        data={"ui_description": HALFLING_LUCK_DESCRIPTION},
    )


HALFLING_LUCK_STATUS = HalflingLuckStatus()

__all__ = ["HalflingLuckStatus", "HALFLING_LUCK_STATUS", "HALFLING_LUCK_DESCRIPTION"]
