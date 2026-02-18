from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

CHARHIDE_GOBLIN_DESCRIPTION = (
    "Otrzymujesz odporność na ogień (1 na 2 poziomy, min 1). "
    "Flat check na zakończenie persistent fire ma DC 10."
)


def CharhideGoblinStatus() -> Status:
    """Heritage: Charhide Goblin."""
    return Status(
        id="charhide_goblin",
        label="Charhide Goblin",
        data={
            "ui_description": CHARHIDE_GOBLIN_DESCRIPTION,
            "damage_resistance": {
                DamageType.FIRE.value: {"per_2_levels": 1, "minimum": 1}
            },
        },
    )


CHARHIDE_GOBLIN_STATUS = CharhideGoblinStatus()

__all__ = [
    "CharhideGoblinStatus",
    "CHARHIDE_GOBLIN_STATUS",
    "CHARHIDE_GOBLIN_DESCRIPTION",
]
