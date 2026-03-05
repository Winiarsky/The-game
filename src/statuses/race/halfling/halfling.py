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
    "Additional language choices: Dwarven, Elven, Gnomish, Goblin.\n"
    "Traits: Halfling, Humanoid.\n"
    "Keen Eyes: lepiej wykrywasz hidden/undetected creatures i łatwiej trafiasz "
    "cele concealed/hidden."
)


def HalflingStatus() -> Status:
    """Status rasy: halfling."""
    return Status(
        id="halfling",
        label="Halfling",
        data={
            "ui_description": HALFLING_DESCRIPTION,
            "ancestry_hp": 6,
            "base_speed_feet": 25,
            "size": "small",
            "ancestry_traits": ["halfling", "humanoid"],
            "ancestry_languages": ["common", "halfling"],
            "ancestry_bonus_languages": [
                "dwarven",
                "elven",
                "gnomish",
                "goblin",
            ],
            "ability_boosts": ["dexterity", "wisdom", "free"],
            "ability_flaw": "strength",
            "grants_statuses": [KEEN_EYES_STATUS],
        },
    )


HALFLING_STATUS = HalflingStatus()

__all__ = ["HalflingStatus", "HALFLING_STATUS", "HALFLING_DESCRIPTION"]
