from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

ARCTIC_ELF_DESCRIPTION = (
    "Cold resistance równa połowie poziomu (minimum 1).\n"
    "Przykład: poziom 1 = Resist Cold 1, poziom 3 = Resist Cold 2.\n"
    "Dodatkowo traktujesz środowiskowe efekty zimna jako o 1 stopień mniej ekstremalne "
    "(hook danych pod przyszłą mechanikę środowiska)."
)


def ArcticElfStatus() -> Status:
    """Heritage: Arctic Elf."""
    return Status(
        id="arctic_elf",
        label="Arctic Elf",
        data={
            "ui_description": ARCTIC_ELF_DESCRIPTION,
            "damage_resistance": {
                DamageType.COLD.value: {"per_2_levels": 1, "minimum": 1}
            },
            "cold_environment_step_reduction": 1,
        },
    )


ARCTIC_ELF_STATUS = ArcticElfStatus()

__all__ = ["ArcticElfStatus", "ARCTIC_ELF_STATUS", "ARCTIC_ELF_DESCRIPTION"]
