from __future__ import annotations

from statuses.base import Status

HUNT_PREY_DESCRIPTION = (
    "Wyznacz ofiare: wybierz jednego przeciwnika jako oznaczony cel. "
    "Akcja wymagana do aktywacji Przewagi lowcy i featow rangera."
)


def HuntPreyStatus() -> Status:
    return Status(
        id="hunt_prey",
        label="Wyznacz ofiare",
        data={
            "ui_description": HUNT_PREY_DESCRIPTION,
            "ui_prompt": HUNT_PREY_DESCRIPTION,
            "allowed_classes": ["ranger"],
        },
    )


HUNT_PREY_STATUS = HuntPreyStatus()

__all__ = ["HUNT_PREY_DESCRIPTION", "HuntPreyStatus", "HUNT_PREY_STATUS"]
