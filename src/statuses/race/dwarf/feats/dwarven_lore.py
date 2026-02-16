from __future__ import annotations

from statuses.base import Status

DWARVEN_LORE_DESCRIPTION = (
    "Otrzymujesz poziom trained w umiejetnosci Crafting, Religion oraz Lore"
)


def DwarvenLoreStatus() -> Status:
    """Feat: Dwarven Lore (opis do UI)."""
    return Status(
        id="dwarven_lore",
        label="Dwarven Lore",
        data={"ui_description": DWARVEN_LORE_DESCRIPTION},
    )


DWARVEN_LORE_STATUS = DwarvenLoreStatus()

__all__ = ["DwarvenLoreStatus", "DWARVEN_LORE_STATUS", "DWARVEN_LORE_DESCRIPTION"]
