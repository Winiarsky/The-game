from __future__ import annotations

from statuses.base import Status

SUDDEN_CHARGE_DESCRIPTION = (
    "Sudden Charge (Open, Flourish): przemieść się 2x i wykonaj melee Strike."
)


def SuddenChargeStatus() -> Status:
    return Status(
        id="sudden_charge",
        label="Sudden Charge",
        data={"ui_description": SUDDEN_CHARGE_DESCRIPTION, "ui_prompt": SUDDEN_CHARGE_DESCRIPTION},
    )


SUDDEN_CHARGE_STATUS = SuddenChargeStatus()

__all__ = ["SuddenChargeStatus", "SUDDEN_CHARGE_STATUS", "SUDDEN_CHARGE_DESCRIPTION"]
