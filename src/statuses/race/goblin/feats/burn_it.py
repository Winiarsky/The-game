from __future__ import annotations

from statuses.base import Status

BURN_IT_DESCRIPTION = (
    "Twoje czary i alchemiczne przedmioty zadające ogień otrzymują status + do obrażeń: "
    "floor(level/2), minimum 1. Dodatkowo +1 status do persistent fire. "
    "(Bonus dodawany automatycznie w promptach obrażeń ognia.)"
)


def BurnItStatus() -> Status:
    """Feat: Burn It! (opis do UI)."""
    return Status(
        id="burn_it",
        label="Burn It!",
        data={"ui_description": BURN_IT_DESCRIPTION},
    )


BURN_IT_STATUS = BurnItStatus()

__all__ = ["BurnItStatus", "BURN_IT_STATUS", "BURN_IT_DESCRIPTION"]
