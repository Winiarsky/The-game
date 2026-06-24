from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

SNOW_GOBLIN_DESCRIPTION = (
    "Masz odporność na zimno równą połowie poziomu (min. 1).\n"
    "Traktujesz środowiskowe efekty zimna jako o 1 stopień mniej ekstremalne."
)


def SnowGoblinStatus() -> Status:
    """Heritage: Snow Goblin."""
    return Status(
        id="snow_goblin",
        label="Snow Goblin",
        data={
            "ui_description": SNOW_GOBLIN_DESCRIPTION,
            "damage_resistance": {
                DamageType.COLD.value: {"per_2_levels": 1, "minimum": 1}
            },
            "cold_environment_step_reduction": 1,
        },
    )


SNOW_GOBLIN_STATUS = SnowGoblinStatus()

__all__ = ["SnowGoblinStatus", "SNOW_GOBLIN_STATUS", "SNOW_GOBLIN_DESCRIPTION"]
