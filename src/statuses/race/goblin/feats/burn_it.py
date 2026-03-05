from __future__ import annotations

from statuses.base import Status

BURN_IT_DESCRIPTION = (
    "Twoje czary i alchemiczne przedmioty zadające fire damage zyskują status bonus "
    "do obrażeń: połowa poziomu czaru lub 1/4 poziomu przedmiotu (min. 1).\n"
    "Dodatkowo zadajesz +1 status do persistent fire damage.\n"
    "W tym silniku bonus liczony jest od poziomu postaci (min. 1), a persistent fire "
    "otrzymuje stałe +1."
)


def BurnItStatus() -> Status:
    """Feat: Burn It! (opis do UI)."""
    return Status(
        id="burn_it",
        label="Burn It!",
        data={
            "ui_description": BURN_IT_DESCRIPTION,
            "burn_it_enabled": True,
            "burn_it_persistent_bonus": 1,
        },
    )


BURN_IT_STATUS = BurnItStatus()

__all__ = ["BurnItStatus", "BURN_IT_STATUS", "BURN_IT_DESCRIPTION"]
