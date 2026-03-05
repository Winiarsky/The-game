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
    "Additional language choices: Draconic, Dwarven, Gnoll, Gnomish, Halfling, Orcish.\n"
    "Traits: Goblin, Humanoid.\n"
    "Darkvision: w ciemności i półmroku widzisz jak w jasnym świetle "
    "(ciemność w odcieniach szarości)."
)


def GoblinStatus() -> Status:
    """Status rasy: goblin."""
    return Status(
        id="goblin",
        label="Goblin",
        data={
            "ui_description": GOBLIN_DESCRIPTION,
            "ancestry_hp": 6,
            "base_speed_feet": 25,
            "size": "small",
            "ancestry_traits": ["goblin", "humanoid"],
            "ancestry_languages": ["common", "goblin"],
            "ancestry_bonus_languages": [
                "draconic",
                "dwarven",
                "gnoll",
                "gnomish",
                "halfling",
                "orcish",
            ],
            "ability_boosts": ["dexterity", "charisma", "free"],
            "ability_flaw": "wisdom",
            "grants_statuses": [DARKVISION_STATUS],
        },
    )


GOBLIN_STATUS = GoblinStatus()

__all__ = ["GoblinStatus", "GOBLIN_STATUS", "GOBLIN_DESCRIPTION"]
