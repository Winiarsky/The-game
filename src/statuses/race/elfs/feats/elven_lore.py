from __future__ import annotations

from statuses.base import Status

ELVEN_LORE_DESCRIPTION = (
    "Otrzymujesz poziom trained dla umiejetnosci: Arcana, Nature oraz Lore"
)


def ElvenLoreStatus() -> Status:
    """Feat: Elven Lore (opis do UI)."""
    return Status(
        id="elven_lore",
        label="Elven Lore",
        data={"ui_description": ELVEN_LORE_DESCRIPTION},
    )


ELVEN_LORE_STATUS = ElvenLoreStatus()

__all__ = ["ElvenLoreStatus", "ELVEN_LORE_STATUS", "ELVEN_LORE_DESCRIPTION"]
