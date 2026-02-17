from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

ARCTIC_ELF_DESCRIPTION = (
    "Zmniejsza obrazenia od lodu o 1 na kazde 2 poziomy (minimum 1)."
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
        },
    )


ARCTIC_ELF_STATUS = ArcticElfStatus()

__all__ = ["ArcticElfStatus", "ARCTIC_ELF_STATUS", "ARCTIC_ELF_DESCRIPTION"]
