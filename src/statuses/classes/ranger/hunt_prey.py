from __future__ import annotations

from statuses.base import Status

HUNT_PREY_DESCRIPTION = (
    "Hunt Prey: wybierz jednego przeciwnika jako hunted prey. "
    "Akcja wymagana do aktywacji Hunter's Edge i featów rangera."
)


def HuntPreyStatus() -> Status:
    return Status(
        id="hunt_prey",
        label="Hunt Prey",
        data={
            "ui_description": HUNT_PREY_DESCRIPTION,
            "ui_prompt": HUNT_PREY_DESCRIPTION,
            "allowed_classes": ["ranger"],
        },
    )


HUNT_PREY_STATUS = HuntPreyStatus()

__all__ = ["HUNT_PREY_DESCRIPTION", "HuntPreyStatus", "HUNT_PREY_STATUS"]
