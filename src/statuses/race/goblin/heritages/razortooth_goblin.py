from __future__ import annotations

from statuses.base import Status

RAZORTOOTH_GOBLIN_DESCRIPTION = (
    "Zyskujesz dodatkową akcję ataku szczękami (1k6 piercing, finesse/unarmed w opisie)."
)


def RazortoothGoblinStatus() -> Status:
    """Heritage: Razortooth Goblin."""
    return Status(
        id="razortooth_goblin",
        label="Razortooth Goblin",
        data={
            "ui_description": RAZORTOOTH_GOBLIN_DESCRIPTION,
            "ui_prompt": "Razortooth Goblin: masz nową akcję 'Razortooth Jaws' (atak wręcz, 1k6 piercing).",
        },
    )


RAZORTOOTH_GOBLIN_STATUS = RazortoothGoblinStatus()

__all__ = [
    "RazortoothGoblinStatus",
    "RAZORTOOTH_GOBLIN_STATUS",
    "RAZORTOOTH_GOBLIN_DESCRIPTION",
]
