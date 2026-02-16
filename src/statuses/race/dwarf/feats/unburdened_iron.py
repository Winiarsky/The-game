from __future__ import annotations

from statuses.base import Status

UNBURDENED_IRON_DESCRIPTION = (
    "Nie otrzymujesz kary do zasiegu ruchu za pancerz oraz redukujesz efekty "
    "magicznego spowolnienia o 5, czyli jesli jakis czar zwolni Cie o 10 stop, "
    "zwalnia Cie tylko o 5. Efekt nie dziala na trudnosci terenu."
)


def UnburdenedIronStatus() -> Status:
    """Feat: Unburdened Iron."""
    return Status(
        id="unburdened_iron",
        label="Unburdened Iron",
        data={
            "ui_description": UNBURDENED_IRON_DESCRIPTION,
            "ignore_armor_move_penalty": True,
            "magical_slow_reduction_feet": 5,
        },
    )


UNBURDENED_IRON_STATUS = UnburdenedIronStatus()

__all__ = ["UnburdenedIronStatus", "UNBURDENED_IRON_STATUS", "UNBURDENED_IRON_DESCRIPTION"]
