from __future__ import annotations

from statuses.base import Status
from statuses.low_light_vision import LOW_LIGHT_VISION_STATUS

GNOME_DESCRIPTION = (
    "Hit Points: 8\n"
    "Size: Small\n"
    "Speed:  25 feet\n"
    "Ability Boosts: Constitution, Charisma, Free\n"
    "Ability Flaw:  Strength\n"
    "Languages: Common, Gnomish, Sylvan\n"
    "Traits:\n"
    "Low-Light Vision\n"
    "You can see in dim light as\n"
    "though it were bright light,\n"
    "and you ignore the concealed\n"
    "condition due to dim light."
)


def GnomeStatus() -> Status:
    """Status rasy: gnome."""
    return Status(
        id="gnome",
        label="Gnome",
        data={
            "ui_description": GNOME_DESCRIPTION,
            "grants_statuses": [LOW_LIGHT_VISION_STATUS],
        },
    )


GNOME_STATUS = GnomeStatus()

__all__ = ["GnomeStatus", "GNOME_STATUS", "GNOME_DESCRIPTION"]
