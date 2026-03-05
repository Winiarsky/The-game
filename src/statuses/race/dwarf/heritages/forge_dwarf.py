from __future__ import annotations

from statuses.base import Status
from damage_types import DamageType

FORGE_DWARF_DESCRIPTION = (
    "Odporność na fire: 1 na 2 poziomy (minimum 1).\n"
    "Przykład: poziom 3 i cios za 7 fire -> redukcja 2, dostajesz 5."
)


def ForgeDwarfStatus() -> Status:
    """Heritage: Forge Dwarf."""
    return Status(
        id="forge_dwarf",
        label="Forge Dwarf",
        data={
            "ui_description": FORGE_DWARF_DESCRIPTION,
            "damage_resistance": {
                DamageType.FIRE.value: {"per_2_levels": 1, "minimum": 1}
            },
        },
    )


FORGE_DWARF_STATUS = ForgeDwarfStatus()

__all__ = ["ForgeDwarfStatus", "FORGE_DWARF_STATUS", "FORGE_DWARF_DESCRIPTION"]
