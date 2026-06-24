from __future__ import annotations

from statuses.base import Status
from statuses.darkvision import DARKVISION_STATUS

UMBRAL_GNOME_DESCRIPTION = (
    "Ciemnosc podziemi jest dla ciebie naturalnym srodowiskiem.\n"
    "Kiedy: stale, od momentu wyboru heritage.\n"
    "Efekt: otrzymujesz Darkvision (grants_statuses: DARKVISION_STATUS), "
    "czyli pelne widzenie w ciemnosci bez potrzeby swiatla."
)


def UmbralGnomeStatus() -> Status:
    """Heritage: Umbral Gnome."""
    return Status(
        id="umbral_gnome",
        label="Umbral Gnome",
        data={
            "ui_description": UMBRAL_GNOME_DESCRIPTION,
            "grants_statuses": [DARKVISION_STATUS],
        },
    )


UMBRAL_GNOME_STATUS = UmbralGnomeStatus()

__all__ = ["UmbralGnomeStatus", "UMBRAL_GNOME_STATUS", "UMBRAL_GNOME_DESCRIPTION"]
