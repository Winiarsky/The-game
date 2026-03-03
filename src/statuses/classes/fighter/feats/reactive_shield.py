from __future__ import annotations

from statuses.base import Status

REACTIVE_SHIELD_DESCRIPTION = (
    "Reactive Shield: reakcja defensywna. "
    "Gdy przeciwnik wykonuje melee Strike przeciw tobie, automatycznie podnosisz tarczę (+2 AC)."
)


def ReactiveShieldStatus() -> Status:
    return Status(
        id="reactive_shield",
        label="Reactive Shield",
        data={"ui_description": REACTIVE_SHIELD_DESCRIPTION, "ui_prompt": REACTIVE_SHIELD_DESCRIPTION},
    )


REACTIVE_SHIELD_STATUS = ReactiveShieldStatus()

__all__ = ["ReactiveShieldStatus", "REACTIVE_SHIELD_STATUS", "REACTIVE_SHIELD_DESCRIPTION"]
