from __future__ import annotations

from statuses.base import Status
from statuses.backgrounds.skill_feats import INTIMIDATING_GLARE_STATUS

RAGING_INTIMIDATION_PROMPT = (
    "Raging Intimidation: podczas Rage możesz używać Demoralize.\n"
    "Dodatkowo otrzymujesz feat Intimidating Glare."
)


def RagingIntimidationStatus() -> Status:
    """Feat: Raging Intimidation."""
    return Status(
        id="raging_intimidation",
        label="Raging Intimidation",
        data={
            "ui_prompt": RAGING_INTIMIDATION_PROMPT,
            "ui_description": RAGING_INTIMIDATION_PROMPT,
            "grants_statuses": [INTIMIDATING_GLARE_STATUS],
        },
    )


RAGING_INTIMIDATION_STATUS = RagingIntimidationStatus()

__all__ = [
    "RagingIntimidationStatus",
    "RAGING_INTIMIDATION_STATUS",
    "RAGING_INTIMIDATION_PROMPT",
]
