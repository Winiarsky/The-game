from __future__ import annotations

from statuses.base import Status

HEALING_HANDS_DESCRIPTION = (
    "Healing Hands: gdy rzucasz Heal, rozliczaj kosci jako d10 zamiast d8."
)


def HealingHandsStatus() -> Status:
    return Status(
        id="healing_hands",
        label="Healing Hands",
        data={
            "ui_description": HEALING_HANDS_DESCRIPTION,
            "ui_prompt": HEALING_HANDS_DESCRIPTION,
            "requires_cleric_font": "heal",
        },
    )


HEALING_HANDS_STATUS = HealingHandsStatus()

__all__ = [
    "HEALING_HANDS_DESCRIPTION",
    "HealingHandsStatus",
    "HEALING_HANDS_STATUS",
]
