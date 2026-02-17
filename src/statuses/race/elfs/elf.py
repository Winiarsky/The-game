from __future__ import annotations

from statuses.base import Status
from statuses.dim_light_vision import DIM_LIGHT_VISION_STATUS

ELF_DESCRIPTION = (
    "Hit Points: 6\n"
    "Size: Medium\n"
    "Speed: 30 feet\n"
    "Ability Boosts: Dexterity, Intelligence, Free\n"
    "Ability Flaw: Constitution\n"
    "Traits: Low-Light Vision (\n"
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
            "grants_statuses": [DIM_LIGHT_VISION_STATUS],
        },
    )


ELF_STATUS = ElfStatus()

__all__ = ["ElfStatus", "ELF_STATUS", "ELF_DESCRIPTION"]
