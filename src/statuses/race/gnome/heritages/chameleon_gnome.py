from __future__ import annotations

from statuses.base import Status

CHAMELEON_GNOME_DESCRIPTION = (
    "Możesz dynamicznie zmieniać barwę skóry i włosów.\n"
    "Gdy twoje ubarwienie z grubsza pasuje do otoczenia, możesz wykonać "
    "pojedynczą akcję dostrojenia barw i zyskać +2 circumstance do Stealth "
    "do czasu wyraźnej zmiany otoczenia.\n"
    "W tym silniku wybór środowiska jest uproszczony: wskazujesz typ terenu, "
    "na którym premia +2 działa."
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
