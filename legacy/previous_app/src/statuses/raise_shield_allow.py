from __future__ import annotations

from .base import Status

RAISE_SHIELD_ALLOW_DESCRIPTION = (
    "Masz atut pozwalajacy wykonac akcje Raise Shield."
)


def RaiseShieldAllowStatus() -> Status:
    return Status(
        id="raise_shield_allow",
        label="Raise Shield (Allow)",
        data={
            "ui_description": RAISE_SHIELD_ALLOW_DESCRIPTION,
            "ui_prompt": RAISE_SHIELD_ALLOW_DESCRIPTION,
        },
    )


RAISE_SHIELD_ALLOW_STATUS = RaiseShieldAllowStatus()

__all__ = [
    "RAISE_SHIELD_ALLOW_DESCRIPTION",
    "RaiseShieldAllowStatus",
    "RAISE_SHIELD_ALLOW_STATUS",
]
