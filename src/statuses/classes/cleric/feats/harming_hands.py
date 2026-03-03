from __future__ import annotations

from statuses.base import Status

HARMING_HANDS_DESCRIPTION = (
    "Harming Hands: gdy rzucasz Harm, rozliczaj kosci jako d10 zamiast d8."
)


def HarmingHandsStatus() -> Status:
    return Status(
        id="harming_hands",
        label="Harming Hands",
        data={
            "ui_description": HARMING_HANDS_DESCRIPTION,
            "ui_prompt": HARMING_HANDS_DESCRIPTION,
            "requires_cleric_font": "harm",
        },
    )


HARMING_HANDS_STATUS = HarmingHandsStatus()

__all__ = [
    "HARMING_HANDS_DESCRIPTION",
    "HarmingHandsStatus",
    "HARMING_HANDS_STATUS",
]
