from __future__ import annotations

from statuses.base import Status

HUMAN_DESCRIPTION = (
    "Hit Points: 8\n"
    "Size: Medium\n"
    "Speed: 25 feet\n"
    "Ability Boosts: Two free ability boosts\n"
    "Languages: Common\n"
    "Additional languages: 1 + Intelligence modifier (jeśli dodatni), "
    "z listy common i innych dostępnych regionalnie.\n"
    "Traits: Human, Humanoid."
)


def HumanStatus() -> Status:
    """Status rasy: human."""
    return Status(
        id="human",
        label="Human",
        data={
            "ui_description": HUMAN_DESCRIPTION,
            "ancestry_hp": 8,
            "base_speed_feet": 25,
            "size": "medium",
            "ancestry_traits": ["human", "humanoid"],
            "ancestry_languages": ["common"],
            "ancestry_bonus_languages_base": 1,
            "ancestry_bonus_languages_source": "int_modifier_positive",
            "ability_boosts": ["free", "free"],
        },
    )


HUMAN_STATUS = HumanStatus()

__all__ = ["HumanStatus", "HUMAN_STATUS", "HUMAN_DESCRIPTION"]
