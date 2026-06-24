from __future__ import annotations

from statuses.base import Status

UNBREAKABLE_GOBLIN_DESCRIPTION = (
    "Masz wyjątkowo wytrzymałe ciało.\n"
    "Z ancestry otrzymujesz 10 HP zamiast 6 (w tym silniku: +4 max HP).\n"
    "Przy upadku liczysz obrażenia jak za połowę przebytego dystansu."
)


def UnbreakableGoblinStatus() -> Status:
    """Heritage: Unbreakable Goblin."""
    return Status(
        id="unbreakable_goblin",
        label="Unbreakable Goblin",
        data={
            "ui_description": UNBREAKABLE_GOBLIN_DESCRIPTION,
            "ui_prompt": "Unbreakable Goblin: +4 max HP (odpowiada 10 HP ancestry zamiast 6).",
            "ancestry_hp_override": 10,
            "max_hp_flat": 4,
            "falling_damage_distance_multiplier": 0.5,
        },
    )


UNBREAKABLE_GOBLIN_STATUS = UnbreakableGoblinStatus()

__all__ = [
    "UnbreakableGoblinStatus",
    "UNBREAKABLE_GOBLIN_STATUS",
    "UNBREAKABLE_GOBLIN_DESCRIPTION",
]
