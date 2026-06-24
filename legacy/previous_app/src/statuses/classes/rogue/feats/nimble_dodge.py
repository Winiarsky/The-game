from __future__ import annotations

from statuses.base import Status

NIMBLE_DODGE_DESCRIPTION = (
    "Nimble Dodge (Reaction): gdy widzisz atakującego i jesteś celem ataku, "
    "otrzymujesz +2 circumstance do AC przeciw wyzwalającemu atakowi."
)


def NimbleDodgeStatus() -> Status:
    return Status(
        id="nimble_dodge",
        label="Nimble Dodge",
        data={
            "ui_description": NIMBLE_DODGE_DESCRIPTION,
            "ui_prompt": NIMBLE_DODGE_DESCRIPTION,
            "allowed_classes": ["rogue"],
        },
    )


NIMBLE_DODGE_STATUS = NimbleDodgeStatus()

__all__ = ["NIMBLE_DODGE_DESCRIPTION", "NimbleDodgeStatus", "NIMBLE_DODGE_STATUS"]
