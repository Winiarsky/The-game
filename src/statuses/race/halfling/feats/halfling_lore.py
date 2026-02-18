from __future__ import annotations

from statuses.base import Status

HALFLING_LORE_DESCRIPTION = (
    "Otrzymujesz trained w Acrobatics i Stealth. Jeśli już jesteś trained, wybierz inny skill. "
    "Ponadto trained w Halfling Lore. (Opisowo)"
)


def HalflingLoreStatus() -> Status:
    """Feat: Halfling Lore (opis do UI)."""
    return Status(
        id="halfling_lore",
        label="Halfling Lore",
        data={"ui_description": HALFLING_LORE_DESCRIPTION},
    )


HALFLING_LORE_STATUS = HalflingLoreStatus()

__all__ = ["HalflingLoreStatus", "HALFLING_LORE_STATUS", "HALFLING_LORE_DESCRIPTION"]
