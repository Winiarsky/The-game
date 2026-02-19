from __future__ import annotations

from statuses.base import Status

HUMAN_DESCRIPTION = (
    "Hit Points: 8\n"
    "Size: Medium\n"
    "Speed: 25 feet\n"
    "Ability Boosts: Two free ability boosts"
)


def HumanStatus() -> Status:
    """Status rasy: human."""
    return Status(
        id="human",
        label="Human",
        data={
            "ui_description": HUMAN_DESCRIPTION,
        },
    )


HUMAN_STATUS = HumanStatus()

__all__ = ["HumanStatus", "HUMAN_STATUS", "HUMAN_DESCRIPTION"]
