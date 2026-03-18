from __future__ import annotations

from statuses.base import Status

RANGED_REPRISAL_DESCRIPTION = (
    "Dystansowa reprymenda: Retributive Strike moze byc wykonany bronia dystansowa, "
    "a gdy cel jest 5 stop poza zasiegiem walki wrecz, mozesz wykonac Krok jako czesc reakcji."
)


def RangedReprisalStatus() -> Status:
    return Status(
        id="ranged_reprisal",
        label="Dystansowa reprymenda",
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
