from __future__ import annotations

from statuses.base import Status

CHAMELEON_GNOME_DESCRIPTION = (
    "Twoja skora i wlosy potrafia szybko dopasowac sie do otoczenia.\n"
    "Kiedy: po dostrojeniu ubarwienia do aktualnego terenu i przy testach Stealth.\n"
    "Efekt: dostajesz +2 circumstance bonus do Stealth w dopasowanym srodowisku; "
    "w silniku zapisujemy wybrany teren (chameleon_terrain), a bonus jest liczony "
    "przez chameleon_stealth_bonus."
)


def ChameleonGnomeStatus() -> Status:
    """Heritage: Chameleon Gnome."""
    return Status(
        id="chameleon_gnome",
        label="Chameleon Gnome",
        data={
            "ui_description": CHAMELEON_GNOME_DESCRIPTION,
            "chameleon_terrain": None,
            "chameleon_stealth_bonus": 2,
        },
    )


CHAMELEON_GNOME_STATUS = ChameleonGnomeStatus()

__all__ = ["ChameleonGnomeStatus", "CHAMELEON_GNOME_STATUS", "CHAMELEON_GNOME_DESCRIPTION"]
