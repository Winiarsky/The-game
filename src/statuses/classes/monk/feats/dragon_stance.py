from __future__ import annotations

from statuses.base import Status

DRAGON_STANCE_DESCRIPTION = (
    "Dragon Stance: atakujesz profilem Dragon Tail (1k10 B, backswing). "
    "Ignorowanie 1. pola difficult terrain: reminder (manual)."
)


def DragonStanceStatus() -> Status:
    return Status(
        id="dragon_stance",
        label="Dragon Stance",
        data={
            "ui_description": DRAGON_STANCE_DESCRIPTION,
            "ui_prompt": DRAGON_STANCE_DESCRIPTION,
        },
    )


DRAGON_STANCE_STATUS = DragonStanceStatus()

__all__ = ["DragonStanceStatus", "DRAGON_STANCE_STATUS", "DRAGON_STANCE_DESCRIPTION"]
