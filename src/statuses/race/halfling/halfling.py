from __future__ import annotations

from statuses.base import Status
from .keen_eyes import KEEN_EYES_STATUS

HALFLING_DESCRIPTION = (
    "Hit Points: 6\n"
    "Size: Small\n"
    "Speed: 25 feet\n"
    "Ability Boosts: Dexterity, Wisdom, Free\n"
    "Ability Flaw: Strength\n"
    "Languages: Common, Halfling\n"
    "Traits: Keen Eyes\n"
    "Your eyes are sharp, allowing\n"
    "you to make out small details\n"
    "about concealed or even\n"
    "invisible creatures that others\n"
    "might miss."
)


def HalflingStatus() -> Status:
    """Status rasy: halfling."""
    return Status(
        id="halfling",
        label="Halfling",
        data={
            "ui_description": HALFLING_DESCRIPTION,
            "grants_statuses": [KEEN_EYES_STATUS],
        },
    )


HALFLING_STATUS = HalflingStatus()

__all__ = ["HalflingStatus", "HALFLING_STATUS", "HALFLING_DESCRIPTION"]
