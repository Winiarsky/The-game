from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

SNOW_GOBLIN_DESCRIPTION = (
    "Otrzymujesz odporność na zimno (1 na 2 poziomy, min 1). "
    "Flat check na zakończenie persistent cold ma DC 10."
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
        },
    )


SNOW_GOBLIN_STATUS = SnowGoblinStatus()

__all__ = ["SnowGoblinStatus", "SNOW_GOBLIN_STATUS", "SNOW_GOBLIN_DESCRIPTION"]
