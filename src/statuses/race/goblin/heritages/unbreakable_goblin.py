from __future__ import annotations

from statuses.base import Status

UNBREAKABLE_GOBLIN_DESCRIPTION = (
    "Otrzymujesz +10 HP z ancestry (do policzenia ręcznie)."
)


def UnbreakableGoblinStatus() -> Status:
    """Heritage: Unbreakable Goblin."""
    return Status(
        id="unbreakable_goblin",
        label="Unbreakable Goblin",
        data={
            "ui_description": UNBREAKABLE_GOBLIN_DESCRIPTION,
            "ui_prompt": "Unbreakable Goblin: +10 HP z ancestry (policz ręcznie).",
        },
    )


UNBREAKABLE_GOBLIN_STATUS = UnbreakableGoblinStatus()

__all__ = [
    "UnbreakableGoblinStatus",
    "UNBREAKABLE_GOBLIN_STATUS",
    "UNBREAKABLE_GOBLIN_DESCRIPTION",
]
