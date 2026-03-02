from __future__ import annotations

from statuses.base import Status

BARDIC_LORE_DESCRIPTION = (
    "Bardic Lore: Recall Knowledge wykonujesz opisowo z advantage "
    "(rzuc 2x k20 i wybierz lepszy wynik)."
)


def BardicLoreStatus() -> Status:
    """Feat: Bardic Lore."""
    return Status(
        id="bardic_lore",
        label="Bardic Lore",
        data={
            "ui_description": BARDIC_LORE_DESCRIPTION,
            "ui_prompt": BARDIC_LORE_DESCRIPTION,
        },
    )


BARDIC_LORE_STATUS = BardicLoreStatus()

__all__ = [
    "BARDIC_LORE_DESCRIPTION",
    "BardicLoreStatus",
    "BARDIC_LORE_STATUS",
]
