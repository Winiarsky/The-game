from __future__ import annotations

from statuses.base import Status

UNBURDENED_IRON_DESCRIPTION = (
    "Ignorujesz karę do Speed z pancerza i zmniejszasz jedną karę do Speed o 5 ft.\n"
    "Przykład: masz speed penalty -10 ft -> z Unburdened Iron działa jako -5 ft.\n"
    "Nie redukuje kosztu trudnego terenu."
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
