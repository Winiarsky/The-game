from __future__ import annotations

from statuses.base import Status

CROSSBOW_ACE_DESCRIPTION = (
    "Crossbow Ace: po Hunt Prey dostajesz +2 circumstance do następnego Strike kuszą. "
    "Dla simple crossbow zwiększ kość obrażeń o 1 stopień."
)


def CrossbowAceStatus() -> Status:
    return Status(
        id="crossbow_ace",
        label="Crossbow Ace",
        data={
            "ui_description": CROSSBOW_ACE_DESCRIPTION,
            "ui_prompt": CROSSBOW_ACE_DESCRIPTION,
            "allowed_classes": ["ranger"],
        },
    )


CROSSBOW_ACE_STATUS = CrossbowAceStatus()

__all__ = ["CROSSBOW_ACE_DESCRIPTION", "CrossbowAceStatus", "CROSSBOW_ACE_STATUS"]
