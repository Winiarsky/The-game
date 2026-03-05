from __future__ import annotations

from statuses.base import Status

DWARVEN_LORE_DESCRIPTION = (
    "Trained: Crafting, Religion, Dwarven Lore.\n"
    "Jeśli już masz trained w którymś z tych skilli, wybierz inny skill ręcznie.\n"
    "Przykład: masz już trained Religion z klasy -> ten slot trained przenieś na inny skill."
)


def DwarvenLoreStatus() -> Status:
    """Feat: Dwarven Lore (opis do UI)."""
    return Status(
        id="dwarven_lore",
        label="Dwarven Lore",
        data={
            "ui_description": DWARVEN_LORE_DESCRIPTION,
            "trained_skills": ["crafting", "religion"],
            "trained_lore": ["dwarven_lore"],
        },
    )


DWARVEN_LORE_STATUS = DwarvenLoreStatus()

__all__ = ["DwarvenLoreStatus", "DWARVEN_LORE_STATUS", "DWARVEN_LORE_DESCRIPTION"]
