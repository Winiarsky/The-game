from __future__ import annotations

from statuses.base import Status
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

ELF_DESCRIPTION = (
    "Hit Points: 6\n"
    "Size: Medium\n"
    "Speed: 30 feet\n"
    "Ability Boosts: Dexterity, Intelligence, Free\n"
    "Ability Flaw: Constitution\n"
    "Languages: Common, Elven\n"
    "Additional languages equal to Intelligence modifier "
    "(Celestial, Draconic, Gnoll, Gnomish, Goblin, Orcish, Sylvan lub regionalne)\n"
    "Traits: Elf, Humanoid, Low-Light Vision\n"
    "Low-Light Vision (\n"
    "You can see in dim light as\n"
    "though it were bright light,\n"
    "so you ignore the concealed\n"
    "condition due to dim light.)"
)


def ElfStatus() -> Status:
    """Status rasy: elf."""
    return Status(
        id="elf",
        label="Elf",
        data={
            "ui_description": ELF_DESCRIPTION,
            "ancestry_hp": 6,
            "base_speed_feet": 30,
            "size": "medium",
            "ancestry_traits": ["elf", "humanoid"],
            "ancestry_languages": ["common", "elven"],
            "ancestry_bonus_languages": [
                "celestial",
                "draconic",
                "gnoll",
                "gnomish",
                "goblin",
                "orcish",
                "sylvan",
            ],
            "ability_boosts": ["dexterity", "intelligence", "free"],
            "ability_flaw": "constitution",
            "grants_statuses": [DIM_LIGHT_VISION_STATUS],
        },
    )


ELF_STATUS = ElfStatus()

__all__ = ["ElfStatus", "ELF_STATUS", "ELF_DESCRIPTION"]
