from __future__ import annotations

from statuses.base import Status

TRAP_FINDER_DESCRIPTION = (
    "Trap Finder: +1 circumstance do Perception vs trapy, AC/saves przeciw trapom "
    "i automatyczna próba wykrycia przy wejściu na pole pułapki."
)


def TrapFinderStatus() -> Status:
    return Status(
        id="trap_finder",
        label="Trap Finder",
        data={
            "ui_description": TRAP_FINDER_DESCRIPTION,
            "ui_prompt": TRAP_FINDER_DESCRIPTION,
            "allowed_classes": ["rogue"],
            "todo_notes": [
                "Pełna obsługa rang Thievery (master/legendary) do disable trap do dopięcia z systemem rang."
            ],
        },
    )


TRAP_FINDER_STATUS = TrapFinderStatus()

__all__ = ["TRAP_FINDER_DESCRIPTION", "TrapFinderStatus", "TRAP_FINDER_STATUS"]
