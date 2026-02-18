from __future__ import annotations

from statuses.base import Status

GOBLIN_LORE_DESCRIPTION = (
    "Otrzymujesz trained w Nature i Stealth. Jeśli już jesteś trained, wybierz inny skill. "
    "Ponadto trained w Goblin Lore. (Opisowo)"
)


def GoblinLoreStatus() -> Status:
    """Feat: Goblin Lore (opis do UI)."""
    return Status(
        id="goblin_lore",
        label="Goblin Lore",
        data={"ui_description": GOBLIN_LORE_DESCRIPTION},
    )


GOBLIN_LORE_STATUS = GoblinLoreStatus()

__all__ = ["GoblinLoreStatus", "GOBLIN_LORE_STATUS", "GOBLIN_LORE_DESCRIPTION"]
