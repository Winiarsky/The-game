from __future__ import annotations

from statuses.base import Status
from statuses.darkvision import DARKVISION_STATUS

DWARF_DESCRIPTION = (
    "Hit Points:  10\n"
    "Size: Medium\n"
    "Speed: 20 feet\n"
    "Ability Boosts: Constitution, Wisdom, Free\n"
    "Ability Flaw: Charisma\n"
    "Languages: Common, Dwarven,\n"
    "Additional languages equal to your Intelligence modifer (if it'spositive). Choose from:  Gnomish, Goblin, Jotun, Orcish, Terran, Undercommon\n"
    "Traits : Darkvision status, Clan Dagger"
)


def DwarfStatus() -> Status:
    """Status rasy: dwarf."""
    return Status(
        id="dwarf",
        label="Dwarf",
        data={
            "ui_description": DWARF_DESCRIPTION,
            "ancestry_hp": 10,
            "base_speed_feet": 20,
            "size": "medium",
            "ancestry_traits": ["dwarf", "humanoid"],
            "ancestry_languages": ["common", "dwarven"],
            "grants_statuses": [DARKVISION_STATUS],
        },
    )


DWARF_STATUS = DwarfStatus()

__all__ = ["DwarfStatus", "DWARF_STATUS", "DWARF_DESCRIPTION"]
