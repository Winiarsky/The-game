from __future__ import annotations

from statuses.base import Status
from statuses.darkvision import DARKVISION_STATUS

GOBLIN_DESCRIPTION = (
    "Hit Points: 6\n"
    "Size: Small\n"
    "Speed: 25 feet\n"
    "Ability Boosts: Dexterity, Charisma, Free\n"
    "Ability Flaw: Wisdom\n"
    "Languages: Common, Goblin\n"
    "Traits: Darkvision\n"
    "You can see in darkness and\n"
    "dim light just as well as you\n"
    "can see in bright light, though\n"
    "your vision in darkness is in\n"
    "black and white."
)


def GoblinStatus() -> Status:
    """Status rasy: goblin."""
    return Status(
        id="goblin",
        label="Goblin",
        data={
            "ui_description": GOBLIN_DESCRIPTION,
            "grants_statuses": [DARKVISION_STATUS],
        },
    )


GOBLIN_STATUS = GoblinStatus()

__all__ = ["GoblinStatus", "GOBLIN_STATUS", "GOBLIN_DESCRIPTION"]
