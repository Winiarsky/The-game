from __future__ import annotations

from damage_types import DamageType
from statuses.base import Status

CHARHIDE_GOBLIN_DESCRIPTION = (
    "Masz odporność na ogień równą połowie poziomu (min. 1).\n"
    "Łatwiej gasisz persistent fire damage: flat check to DC 10 zamiast 15.\n"
    "Przy odpowiedniej pomocy sojusznika DC spada do 5 (opisowo)."
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
            "persistent_damage_flat_check_dc_overrides": {
                DamageType.FIRE.value: 10
            },
            "persistent_damage_flat_check_dc_with_help_overrides": {
                DamageType.FIRE.value: 5
            },
        },
    )


CHARHIDE_GOBLIN_STATUS = CharhideGoblinStatus()

__all__ = [
    "CharhideGoblinStatus",
    "CHARHIDE_GOBLIN_STATUS",
    "CHARHIDE_GOBLIN_DESCRIPTION",
]
