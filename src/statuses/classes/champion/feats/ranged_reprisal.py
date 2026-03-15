from __future__ import annotations

from statuses.base import Status

RANGED_REPRISAL_DESCRIPTION = (
    "Ranged Reprisal: Retributive Strike moze byc wykonany bronia dystansowa, "
    "a gdy cel jest 5 stop poza zasiegiem melee, mozesz Step jako czesc reakcji."
)


def RangedReprisalStatus() -> Status:
    return Status(
        id="ranged_reprisal",
        label="Ranged Reprisal",
        data={
            "ui_description": RANGED_REPRISAL_DESCRIPTION,
            "ui_prompt": RANGED_REPRISAL_DESCRIPTION,
            "requires_champion_cause": "paladin",
        },
    )


RANGED_REPRISAL_STATUS = RangedReprisalStatus()

__all__ = [
    "RANGED_REPRISAL_DESCRIPTION",
    "RangedReprisalStatus",
    "RANGED_REPRISAL_STATUS",
]
